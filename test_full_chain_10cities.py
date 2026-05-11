"""
10 城市 full_chain v2 回归验证脚本

用法:
    python test_full_chain_10cities.py                    # 本地
    python test_full_chain_10cities.py --url https://hexa-blueprint-api-production.up.railway.app

输出:
    - 控制台汇总表
    - docs/test_reports/10cities_report_{timestamp}.md
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
API_KEY = "hexa-tour-2024"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# 10 城市测试用例 (city, days, interests, need_guide, need_car)
TEST_CASES = [
    ("北京", 2, ["history", "culture"], True, True),
    ("上海", 3, ["history", "culture"], False, True),
    ("广州", 2, ["history", "culture"], True, True),
    ("重庆", 3, ["nature", "food"], False, True),
    ("西安", 2, ["history", "culture"], True, True),
    ("阳朔", 2, ["nature", "photography"], False, True),
    ("张家界", 2, ["nature", "photography"], True, True),
    ("贵州", 4, ["culture", "nature"], False, True),
    ("云南", 5, ["nature", "photography", "culture"], True, True),
    ("成都", 2, ["food", "culture"], False, True),
]


def test_city(city: str, days: int, interests: list, need_guide: bool, need_car: bool, url: str) -> dict:
    payload = {
        "city": city,
        "days": days,
        "adults": 2,
        "children": 0,
        "seniors": 0,
        "is_peak": True,
        "need_guide": need_guide,
        "need_private_car": need_car,
        "interests": interests,
        "selected_optional_item_codes": [],
    }
    start = time.time()
    try:
        resp = requests.post(f"{url}/api/v2/full_chain", json=payload, headers=HEADERS, timeout=60)
        elapsed = round(time.time() - start, 2)
        data = resp.json()
        success = data.get("success", False)
        error = data.get("error", None)
        product = ""
        grand_total = 0
        itinerary_len = 0
        has_pricing = False
        has_plan = False
        has_product_match = False

        if success:
            pm = data.get("product_match", {})
            candidates = pm.get("candidates", [])
            if candidates:
                has_product_match = True
                product = candidates[0].get("product", {}).get("product_name", "")
                product_id = candidates[0].get("product", {}).get("product_id", "")

            has_plan = bool(data.get("plan"))
            pricing = data.get("pricing", {})
            summary = pricing.get("summary", {})
            if summary:
                has_pricing = True
                grand_total = summary.get("grand_total", 0)

            md = data.get("itinerary_markdown", "")
            itinerary_len = len(md)

        return {
            "city": city,
            "days": days,
            "success": success,
            "product": product,
            "grand_total": grand_total,
            "itinerary_len": itinerary_len,
            "has_pricing": has_pricing,
            "has_plan": has_plan,
            "has_product_match": has_product_match,
            "error": error,
            "elapsed": elapsed,
            "status_code": resp.status_code,
        }
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return {
            "city": city,
            "days": days,
            "success": False,
            "product": "",
            "grand_total": 0,
            "itinerary_len": 0,
            "has_pricing": False,
            "has_plan": False,
            "has_product_match": False,
            "error": str(e),
            "elapsed": elapsed,
            "status_code": 0,
        }


def generate_report(results: list, url: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).resolve().parent / "docs" / "test_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"10cities_report_{timestamp}.md"

    passed = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    lines = []
    lines.append(f"# 10 城市 full_chain 回归验证报告\n")
    lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    lines.append(f"**目标**: `{url}`  \n")
    lines.append(f"**结果**: {passed} ✅ / {failed} ❌ / {len(results)} 总计\n")

    # Summary table
    lines.append("## 汇总\n")
    lines.append("| 城市 | 天数 | 状态 | 产品 | 总价(¥) | 行程长度 | 耗时(s) | 备注 |")
    lines.append("|------|------|------|------|---------|----------|---------|------|")
    for r in results:
        status = "✅" if r["success"] else "❌"
        err = (r["error"][:50] + "..") if r.get("error") else "-"
        product = r["product"][:30] if r["product"] else "-"
        total = f"¥{r['grand_total']:,.0f}" if r["grand_total"] else "-"
        lines.append(f"| {r['city']} | {r['days']}天 | {status} | {product} | {total} | {r['itinerary_len']}字 | {r['elapsed']}s | {err} |")

    # Detail section for failures
    failures = [r for r in results if not r["success"]]
    if failures:
        lines.append("\n## 失败详情\n")
        for f in failures:
            lines.append(f"### {f['city']} ({f['days']}天)\n")
            lines.append(f"- 状态码: {f['status_code']}")
            lines.append(f"- 错误: {f['error']}")
            lines.append(f"- 耗时: {f['elapsed']}s\n")

    # Detail section for passes — key measurements
    pass_details = [r for r in results if r["success"]]
    if pass_details:
        lines.append("\n## 通过城市关键指标\n")
        for r in pass_details:
            issues = []
            if not r["has_pricing"]:
                issues.append("缺少报价")
            if not r["has_plan"]:
                issues.append("缺少行程")
            if not r["has_product_match"]:
                issues.append("缺少产品匹配")
            if r["itinerary_len"] < 100:
                issues.append("行程内容过短")
            status = "✅" if not issues else "⚠️ " + ", ".join(issues)
            lines.append(f"- **{r['city']}** ({r['days']}天): {r['product']} | ¥{r['grand_total']:,.0f} | {r['itinerary_len']}字 | {r['elapsed']}s | {status}")

    lines.append(f"\n---\n*报告由 test_full_chain_10cities.py 自动生成*")

    report = "\n".join(lines) + "\n"
    report_path.write_text(report, encoding="utf-8")
    return report_path, report


def main():
    parser = argparse.ArgumentParser(description="10 城市 full_chain 回归验证")
    parser.add_argument("--url", default=BASE_URL, help="API 地址（默认 localhost:8000）")
    args = parser.parse_args()

    url = args.url.rstrip("/")
    print(f"🔍 测试目标: {url}")
    print(f"🔍 共 {len(TEST_CASES)} 个城市\n")

    results = []
    for i, (city, days, interests, need_guide, need_car) in enumerate(TEST_CASES):
        print(f"  [{i+1}/{len(TEST_CASES)}] {city} {days}天 ... ", end="", flush=True)
        result = test_city(city, days, interests, need_guide, need_car, url)
        results.append(result)

        if result["success"]:
            print(f"✅  ¥{result['grand_total']:,.0f}  {result['itinerary_len']}字  {result['elapsed']}s")
        else:
            print(f"❌  {result.get('error', '未知错误')[:60]}  {result['elapsed']}s")

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["success"])
    print(f"结果: {passed}/{len(results)} 通过")
    for r in results:
        icon = "✅" if r["success"] else "❌"
        print(f"  {icon} {r['city']} ({r['days']}天)  {r['product'][:25] if r['product'] else '-':25s}  ¥{r['grand_total']:>8,.0f}  {r['elapsed']}s")

    # Save report
    report_path, _ = generate_report(results, url)
    print(f"\n📄 报告已保存: {report_path}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
