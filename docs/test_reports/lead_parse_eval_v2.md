# Lead Parse Eval Report

- Generated at: 2026-09-08T04:45:48Z
- Cases: 50
- Field accuracy: 97.78%
- Assertions: 264 / 270

## Cases

### lead_parse_001_optional_car — PASS

### lead_parse_002_senior_mobility — PASS

### lead_parse_003_retired_not_senior — PASS

### lead_parse_004_family_food — PASS

### lead_parse_005_missing_destination — PASS

### lead_parse_006_airport_transfer — PASS

### lead_parse_007_no_guide_no_car — FAIL

Failures:
- interests_contains: expected ['local_markets', 'local_food'], got ['local_food', 'food', 'local_life']

### lead_parse_008_budget_per_person — PASS

### lead_parse_009_hotel_view — FAIL

Failures:
- hotel_tier: expected 'premium', got None
- interests_contains: expected ['photography', 'fine_dining'], got ['photography', 'food']

### lead_parse_010_dietary_notes — PASS

### lead_parse_011_multi_city — PASS

### lead_parse_012_must_have — PASS

### lead_parse_013_avoid_shopping — PASS

### lead_parse_014_flexible_dates — PASS

### lead_parse_015_child_age — PASS

### lead_parse_016_luxury_budget — FAIL

Failures:
- interests_contains: expected ['scenic_views', 'photography'], got ['photography', 'scenic_view']

### lead_parse_017_budget_total — PASS

### lead_parse_018_airport_transfer_false — PASS

### lead_parse_019_senior_group — PASS

### lead_parse_020_language_chinese — FAIL

Failures:
- interests_contains: expected ['history', 'hutong'], got ['history', 'local_life']

### lead_parse_021_unknown_days — PASS

### lead_parse_022_hotel_special_requirement — PASS

### lead_parse_023_transport_preference — FAIL

Failures:
- transport_preference: expected 'high-speed train', got None

### lead_parse_024_food_allergy — PASS

### lead_parse_025_photography_quiet — PASS

### lead_parse_026_budget_both_total_and_per_person — PASS

### lead_parse_027_guide_maybe_null — PASS

### lead_parse_028_car_conditional_null — PASS

### lead_parse_029_arrival_only_transfer — PASS

### lead_parse_030_multigeneration_family — PASS

### lead_parse_031_hotel_for_senior_not_senior_guest — PASS

### lead_parse_032_nights_not_days — PASS

### lead_parse_033_five_star_luxury — PASS

### lead_parse_034_negative_to_avoid — PASS

### lead_parse_035_mixed_language — PASS

### lead_parse_036_usd_currency_notes — PASS

### lead_parse_037_greeting_noise — PASS

### lead_parse_038_grown_children_stay_home — PASS

### lead_parse_039_driver_guide — PASS

### lead_parse_040_unsupported_province_verbatim — PASS

### lead_parse_041_senior_and_child_boundary — PASS

### lead_parse_042_exact_date_range — PASS

### lead_parse_043_no_budget_no_luxury_flag — PASS

### lead_parse_044_active_sixty_not_senior — PASS

### lead_parse_045_contradictory_guide_resolved — PASS

### lead_parse_046_inconsistent_budget_both_stated — PASS

### lead_parse_047_offbeat_avoid_touristy — PASS

### lead_parse_048_guide_and_car_full_trip — PASS

### lead_parse_049_multi_signal_passenger_count — PASS

### lead_parse_050_allergy_and_avoid_together — PASS
