# Lead Parse Eval Report

- Generated at: 2026-09-07T11:03:07Z
- Cases: 5
- Field accuracy: 70.37%
- Assertions: 19 / 27

## Cases

### lead_parse_001_optional_car — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- sales_notes_contains: expected ['private_car'], got unsupported

### lead_parse_002_senior_mobility — FAIL

Failures:
- ReadTimeout: HTTPSConnectionPool(host='dashscope.aliyuncs.com', port=443): Read timed out. (read timeout=30.0)

### lead_parse_003_retired_not_senior — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- season: expected 'next spring', got 'spring'

### lead_parse_004_family_food — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']
- travel_style_contains: expected ['family_friendly', 'slow_pace'], got unsupported

### lead_parse_005_missing_destination — FAIL

Failures:
- destination_cities: expected [], got ['China']
- season: expected 'next autumn', got 'autumn'
