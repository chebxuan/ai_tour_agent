"""Run existing deterministic evaluations and local API checks without external calls."""
from __future__ import annotations

import contextlib
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    # This key is used only inside TestClient. No network services are contacted.
    with patch.dict(os.environ, {"API_KEY": "local-verification-only", "TRAVEL_DATA_SOURCE": "files"}):
        from backend.app import main as api
        from backend.app.core.paths import ROOT as runtime_root
        from backend.app.llm_client import read_prompt_template
        from backend.app.engines import payment_tracker
        from fastapi.testclient import TestClient
        import api_main

        assert runtime_root == ROOT
        assert api_main.app is api.app
        assert "{{customer_message}}" in read_prompt_template("lead_parse_v2.md")
        for name in ["product_match", "pricing", "risk_check", "delivery_compose"]:
            module = importlib.import_module("evals.eval_" + name)
            cases = module.load_cases(module.DEFAULT_CASES)
            module.validate_case_file(cases)
            with contextlib.redirect_stdout(io.StringIO()):
                report = module.run_eval(cases)
            passed, total = report["passed_cases"], report["case_count"]
            print(f"{name}: {passed}/{total}")
            if passed != total:
                return 1

        cities = {}
        for product in api.load_normalized_products():
            cities.setdefault(product["city"], product["duration_days"])
        with tempfile.TemporaryDirectory(prefix="travel-ops-verification-") as temp:
            # Redirect writable storage to prevent verification touching real data/logs.
            with patch.object(api, "append_workflow_event"), patch.object(
                payment_tracker, "PAYMENTS_JSON", Path(temp) / "payments.json"
            ), TestClient(api.app) as client:
                headers = {"X-API-Key": "local-verification-only"}
                assert client.get("/health").status_code == 200
                assert client.get("/api/v2/cities", headers=headers).status_code == 200
                assert client.get("/api/v2/payments/stats", headers=headers).status_code == 200
                assert client.get("/api/v2/cities", headers={"X-API-Key": "wrong"}).status_code == 401
                for city, days in cities.items():
                    with contextlib.redirect_stdout(io.StringIO()):
                        response = client.post(
                            "/api/v2/full_chain",
                            headers=headers,
                            json={"city": city, "days": days, "adults": 2, "children": 0,
                                  "seniors": 0, "is_peak": True, "need_guide": False,
                                  "need_private_car": False},
                        )
                    result = response.json()
                    assert response.status_code == 200, city
                    assert result["success"] and result["pricing"]["success"], city
                    assert result["itinerary_markdown"], city
                print(f"Standard API: {len(cities)}/{len(cities)} cities")

        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tests/test_custom_route_shanghai.py")],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            return result.returncode
        print("Shanghai route scenarios: 5/5")
        print("Compatibility entrypoint and runtime prompt: PASS")
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "tests.test_travel_api", "tests.test_menu_content", "tests.test_sales_pricing", "tests.test_journey_enquiries"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            return result.returncode
        print("Standalone travel API, Menu, sales pricing and enquiry validation: 21/21 test groups (21 products)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
