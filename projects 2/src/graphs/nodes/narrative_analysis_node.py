import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from graphs.state import NarrativeAnalysisInput, NarrativeAnalysisOutput


def narrative_analysis_node(state: NarrativeAnalysisInput, config: RunnableConfig, runtime: Runtime[Context]) -> NarrativeAnalysisOutput:
    """
    title: 资源图谱地标提取
    desc: 使用大模型从游记中精准提取所有物理存在的地标实体，输出结构化的地标数组
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 使用 jinja2 模板渲染用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"raw_content": state.raw_content})
    
    # 初始化 LLM 客户端
    client = LLMClient(ctx=ctx)
    
    # 构建消息
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    # 调用大模型（添加重试机制）
    max_retries = 2
    retry_count = 0
    response = None
    
    while retry_count <= max_retries:
        try:
            response = client.invoke(
                messages=messages,
                model=llm_config.get("model", "doubao-seed-2-0-pro-260215"),
                temperature=llm_config.get("temperature", 0.5),
                top_p=llm_config.get("top_p", 0.9),
                max_completion_tokens=llm_config.get("max_completion_tokens", 4000),
                thinking=llm_config.get("thinking", "disabled")
            )
            break
        except Exception as e:
            retry_count += 1
            if retry_count > max_retries:
                # 重试失败，返回空数组
                analysis_result = {
                    "nodes": [],
                    "error": f"大模型调用失败（已重试{max_retries}次）：{str(e)}"
                }
                return NarrativeAnalysisOutput(analysis_result=analysis_result)
    
    # 处理响应内容
    content = response.content
    if isinstance(content, list):
        # 如果是列表，尝试提取文本
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        content = " ".join(text_parts)
    
    # 提取 JSON 部分（去除可能的 markdown 标记）
    content_str = str(content).strip()
    
    # 如果内容为空，直接返回空数组
    if not content_str:
        analysis_result = {
            "nodes": [],
            "error": "原始内容为空"
        }
        return NarrativeAnalysisOutput(analysis_result=analysis_result)
    
    if content_str.startswith("```json"):
        content_str = content_str[7:]
    if content_str.startswith("```"):
        content_str = content_str[3:]
    if content_str.endswith("```"):
        content_str = content_str[:-3]
    content_str = content_str.strip()
    
    # 解析 JSON
    try:
        parsed_result = json.loads(content_str)
        
        # 确保返回的是数组
        if isinstance(parsed_result, list):
            # 如果是数组，直接使用
            analysis_result = {
                "nodes": parsed_result,
                "count": len(parsed_result)
            }
        elif isinstance(parsed_result, dict):
            # 如果是字典，检查是否有 nodes 字段
            if "nodes" in parsed_result:
                analysis_result = parsed_result
            else:
                # 如果是单个对象，包装成数组
                analysis_result = {
                    "nodes": [parsed_result],
                    "count": 1
                }
        else:
            analysis_result = {
                "nodes": [],
                "error": f"解析结果类型不支持：{type(parsed_result)}"
            }
    except json.JSONDecodeError as e:
        # 如果解析失败，返回空数组
        analysis_result = {
            "nodes": [],
            "error": f"JSON解析失败，原始内容：{content_str[:500]}，错误：{str(e)}"
        }
    
    return NarrativeAnalysisOutput(analysis_result=analysis_result)
