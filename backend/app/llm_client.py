from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar
from uuid import uuid4

import requests
from pydantic import BaseModel, ValidationError

from backend.app.schemas import LeadJSON


from backend.app.core.paths import ROOT
PROMPT_DIR = Path(__file__).resolve().parent / "resources" / "prompts"
LOG_DIR = ROOT / "logs"
LLM_CALL_LOG = LOG_DIR / "llm_calls.jsonl"

T = TypeVar("T", bound=BaseModel)


class LLMConfigurationError(RuntimeError):
    pass


class LLMParseError(RuntimeError):
    pass


def read_prompt_template(prompt_name: str) -> str:
    path = PROMPT_DIR / prompt_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, values: Dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def log_llm_call(record: Dict[str, Any]) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    with LLM_CALL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text.strip()).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]

    raise LLMParseError("No JSON object found in model output")


def parse_json_output(raw_text: str) -> Dict[str, Any]:
    json_text = _extract_json_text(raw_text)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMParseError("Model output must be a JSON object")
    return data


def validate_with_schema(data: Dict[str, Any], schema: Type[T]) -> T:
    try:
        return schema.model_validate(data)
    except ValidationError:
        raise


def _chat_completion_request(messages: list[Dict[str, str]], model: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMConfigurationError("OPENAI_API_KEY is not configured")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    url = f"{base_url}/chat/completions"

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def call_model(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload = _chat_completion_request(
        messages=[{"role": "user", "content": prompt}],
        model=model_name,
    )
    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage", {})
    return {
        "model": model_name,
        "content": content,
        "usage": usage,
    }


def _build_fix_prompt(raw_output: str, error: str, schema_name: str) -> str:
    return (
        "Fix the following model output so it becomes valid JSON matching "
        f"the {schema_name} schema. Return JSON only. Do not add explanation. "
        "Do not invent new customer facts.\n\n"
        f"Validation or parsing error:\n{error}\n\n"
        f"Previous output:\n{raw_output}"
    )


def parse_lead_text(
    customer_message: str,
    *,
    lead_id: Optional[str] = None,
    source_channel: Optional[str] = None,
    source_id: Optional[str] = None,
    # Default to lead_parse_v2: it fixed all 65 v1 field-level failures on the 50-case eval
    # (75.93% -> 97.78%). Callers can still pass prompt_version="lead_parse_v1" explicitly.
    prompt_version: str = "lead_parse_v2",
) -> LeadJSON:
    request_id = f"req_{uuid4().hex[:10]}"
    started = time.perf_counter()
    prompt_template = read_prompt_template(f"{prompt_version}.md")
    prompt = render_prompt(prompt_template, {"customer_message": customer_message})
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    log_record: Dict[str, Any] = {
        "request_id": request_id,
        "task_name": "lead_parse",
        "prompt_version": prompt_version,
        "model_name": model_name,
        "input_chars": len(customer_message),
        "success": False,
        "error_type": None,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    raw_output = ""
    try:
        model_response = call_model(prompt, model=model_name)
        raw_output = model_response["content"]
        usage = model_response.get("usage", {})
        log_record.update(
            {
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "output_chars": len(raw_output),
            }
        )

        try:
            data = parse_json_output(raw_output)
            lead = validate_with_schema(data, LeadJSON)
        except (LLMParseError, ValidationError) as exc:
            fix_prompt = _build_fix_prompt(raw_output, str(exc), "LeadJSON")
            fixed_response = call_model(fix_prompt, model=model_name)
            fixed_output = fixed_response["content"]
            log_record["retry_used"] = True
            data = parse_json_output(fixed_output)
            lead = validate_with_schema(data, LeadJSON)

        update = {}
        if lead_id:
            update["lead_id"] = lead_id
        if source_channel or source_id or customer_message:
            source = lead.source.model_copy(
                update={
                    "channel": source_channel if source_channel is not None else lead.source.channel,
                    "source_id": source_id if source_id is not None else lead.source.source_id,
                    "raw_text": lead.source.raw_text or customer_message,
                }
            )
            update["source"] = source
        if not lead.created_at:
            update["created_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        lead = lead.model_copy(update=update)

        log_record["success"] = True
        return lead
    except LLMConfigurationError:
        log_record["error_type"] = "configuration_error"
        raise
    except ValidationError:
        log_record["error_type"] = "pydantic_validation_error"
        raise
    except LLMParseError:
        log_record["error_type"] = "json_parse_error"
        raise
    except Exception as exc:
        log_record["error_type"] = exc.__class__.__name__
        raise
    finally:
        log_record["latency_ms"] = round((time.perf_counter() - started) * 1000)
        log_llm_call(log_record)
