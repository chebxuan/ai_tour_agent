# Lead Parse Eval Report

- Generated at: 2026-09-08T04:46:23Z
- Cases: 50
- Field accuracy: 75.93%
- Assertions: 205 / 270

## Cases

### lead_parse_001_optional_car — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_002_senior_mobility — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']
- avoid_contains: expected ['long_walking', 'crowded_tourist_spots'], got ['crowded_places']
- travel_style_contains: expected ['senior_friendly', 'slow_pace'], got ['senior_friendly', 'long_walking']

### lead_parse_003_retired_not_senior — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- season: expected 'next spring', got 'spring'

### lead_parse_004_family_food — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']
- travel_style_contains: expected ['family_friendly', 'slow_pace'], got ['slow_pace']

### lead_parse_005_missing_destination — FAIL

Failures:
- destination_cities: expected [], got ['China']
- season: expected 'next autumn', got 'autumn'

### lead_parse_006_airport_transfer — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_007_no_guide_no_car — FAIL

Failures:
- destination_cities: expected ['广州'], got ['Guangzhou']

### lead_parse_008_budget_per_person — FAIL

Failures:
- destination_cities: expected ['西安'], got ["Xi'an"]
- avoid_contains: expected ['luxury_hotels'], got []

### lead_parse_009_hotel_view — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_010_dietary_notes — FAIL

Failures:
- destination_cities: expected ['重庆'], got ['Chongqing']

### lead_parse_011_multi_city — FAIL

Failures:
- destination_cities: expected ['北京', '西安'], got ['Beijing', "Xi'an"]

### lead_parse_012_must_have — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_013_avoid_shopping — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_014_flexible_dates — FAIL

Failures:
- destination_cities: expected ['张家界'], got ['Zhangjiajie']

### lead_parse_015_child_age — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- interests_contains: expected ['Disneyland'], got []

### lead_parse_016_luxury_budget — FAIL

Failures:
- destination_cities: expected ['云南'], got ['Yunnan']
- travel_style_contains: expected ['honeymoon'], got []

### lead_parse_017_budget_total — FAIL

Failures:
- destination_cities: expected ['阳朔'], got ['Yangshuo']

### lead_parse_018_airport_transfer_false — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']

### lead_parse_019_senior_group — FAIL

Failures:
- destination_cities: expected ['贵州'], got ['Guizhou']

### lead_parse_020_language_chinese — PASS

### lead_parse_021_unknown_days — FAIL

Failures:
- destination_cities: expected ['广州'], got ['Guangzhou']
- interests_contains: expected ['history', 'local_food', 'local_life'], got ['history', 'cantonese_food', 'local_life']

### lead_parse_022_hotel_special_requirement — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_023_transport_preference — FAIL

Failures:
- destination_cities: expected ['西安'], got ["Xi'an"]

### lead_parse_024_food_allergy — FAIL

Failures:
- destination_cities: expected ['重庆'], got ['Chongqing']

### lead_parse_025_photography_quiet — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- interests_contains: expected ['local_life', 'architecture', 'coffee', 'photography'], got ['local_life', 'art_deco_buildings', 'coffee_shops', 'photography']

### lead_parse_026_budget_both_total_and_per_person — FAIL

Failures:
- destination_cities: expected ['阳朔'], got ['Yangshuo']

### lead_parse_027_guide_maybe_null — FAIL

Failures:
- destination_cities: expected ['重庆'], got ['Chongqing']

### lead_parse_028_car_conditional_null — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_029_arrival_only_transfer — FAIL

Failures:
- destination_cities: expected ['西安'], got ["Xi'an"]

### lead_parse_030_multigeneration_family — FAIL

Failures:
- destination_cities: expected ['广州'], got ['Guangzhou']
- interests_contains: expected ['local_food'], got ['dim_sum', 'classical_gardens']

### lead_parse_031_hotel_for_senior_not_senior_guest — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']

### lead_parse_032_nights_not_days — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']
- sales_notes_contains: expected ['nights'], got '(empty)'

### lead_parse_033_five_star_luxury — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_034_negative_to_avoid — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']

### lead_parse_035_mixed_language — PASS

### lead_parse_036_usd_currency_notes — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']
- budget_max_per_person: expected None, got 600.0

### lead_parse_037_greeting_noise — FAIL

Failures:
- destination_cities: expected ['云南'], got ['Yunnan']

### lead_parse_038_grown_children_stay_home — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_039_driver_guide — FAIL

Failures:
- destination_cities: expected ['重庆'], got ['Chongqing']
- need_guide: expected None, got True

### lead_parse_040_unsupported_province_verbatim — FAIL

Failures:
- destination_cities: expected ['山西'], got ['Shanxi province']

### lead_parse_041_senior_and_child_boundary — FAIL

Failures:
- destination_cities: expected ['厦门'], got ['Xiamen']

### lead_parse_042_exact_date_range — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_043_no_budget_no_luxury_flag — FAIL

Failures:
- destination_cities: expected ['云南'], got ['Yunnan']

### lead_parse_044_active_sixty_not_senior — FAIL

Failures:
- destination_cities: expected ['张家界'], got ['Zhangjiajie']

### lead_parse_045_contradictory_guide_resolved — FAIL

Failures:
- destination_cities: expected ['上海'], got ['Shanghai']

### lead_parse_046_inconsistent_budget_both_stated — FAIL

Failures:
- destination_cities: expected ['西安'], got ["Xi'an"]

### lead_parse_047_offbeat_avoid_touristy — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']
- interests_contains: expected ['tea_culture', 'local_food', 'local_life'], got ['tea_culture', 'local_food']
- avoid_contains: expected ['crowded_tourist_spots'], got ['famous_tourist_sites']

### lead_parse_048_guide_and_car_full_trip — FAIL

Failures:
- destination_cities: expected ['北京'], got ['Beijing']

### lead_parse_049_multi_signal_passenger_count — FAIL

Failures:
- destination_cities: expected ['广州'], got ['Guangzhou']

### lead_parse_050_allergy_and_avoid_together — FAIL

Failures:
- destination_cities: expected ['成都'], got ['Chengdu']
- avoid_contains: expected ['smoke'], got ['heavy_smoking']
