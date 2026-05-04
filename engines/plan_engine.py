from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from schemas import PlanActivity, PlanDay, PlanObject, SelectedOptionalItem, SelectedProduct, TravelWindow


TIME_SLOTS = ["morning", "afternoon", "evening"]
OPTIONAL_MARKERS = ["(可选)", "(建议)", "(推荐)"]


def clean_activity_title(name: str) -> str:
    title = (name or "").strip()
    for marker in OPTIONAL_MARKERS:
        title = title.replace(marker, "")
    return title.strip()


def infer_time_slot(position: int, total: int) -> str:
    if total <= 1:
        return "custom"
    if total == 2:
        return TIME_SLOTS[min(position, 1)]
    if total == 3:
        return TIME_SLOTS[min(position, 2)]
    if position == 0:
        return "morning"
    if position == total - 1:
        return "evening"
    return "afternoon"


def infer_activity_type(title: str) -> str:
    normalized = title.lower()
    if any(keyword in normalized for keyword in ["hotel", "入住", "退房"]):
        return "hotel"
    if any(keyword in normalized for keyword in ["transfer", "airport", "train", "flight", "station", "接机", "送机"]):
        return "transport"
    if any(keyword in normalized for keyword in ["dinner", "lunch", "breakfast", "food", "duck", "hotpot", "烤鸭", "涮肉", "小酌", "用餐"]):
        return "meal"
    if any(keyword in normalized for keyword in ["show", "opera", "performance", "体验", "酒馆", "京剧"]):
        return "experience"
    if any(keyword in normalized for keyword in ["walk", "park", "hutong", "beach", "胡同", "公园"]):
        return "sightseeing"
    return "attraction"


def infer_day_theme(activities: List[str]) -> Optional[str]:
    cleaned = [clean_activity_title(activity) for activity in activities if clean_activity_title(activity)]
    if not cleaned:
        return None
    preview = " / ".join(cleaned[:2])
    if len(cleaned) > 2:
        return f"{preview} and more"
    return preview


def build_transport_notes(day_number: int, total_days: int, city: str) -> List[str]:
    notes: List[str] = []
    if day_number == 1:
        notes.append(f"Arrival and local coordination for {city} should be confirmed before this day starts.")
    if total_days > 1 and day_number == total_days:
        notes.append(f"Departure timing and final transfer arrangement for {city} should be reconfirmed for the last day.")
    return notes


def build_plan_activities_for_day(
    city: str,
    product_id: str,
    day_number: int,
    raw_activities: List[str],
    selected_optional_items: List[SelectedOptionalItem],
) -> List[PlanActivity]:
    selected_option_titles = {clean_activity_title(item.name or "") for item in selected_optional_items if item.selected and (item.name or "").strip()}
    selected_option_codes = {item.code for item in selected_optional_items if item.selected}

    activities: List[PlanActivity] = []
    total = len(raw_activities)
    for index, raw_name in enumerate(raw_activities):
        cleaned_title = clean_activity_title(raw_name)
        included = True
        notes: List[str] = []

        if any(marker in raw_name for marker in OPTIONAL_MARKERS):
            included = cleaned_title in selected_option_titles
            if included:
                notes.append("Selected optional item included in current plan scope.")
            else:
                notes.append("Optional or recommended stop shown as a planning reference, not confirmed in base scope.")
        elif selected_option_codes and cleaned_title in selected_option_titles:
            included = True
            notes.append("Matched to selected optional item.")

        activities.append(
            PlanActivity(
                activity_id=f"{product_id}-D{day_number}-A{index + 1}",
                city=city,
                title=cleaned_title or raw_name,
                source_product_id=product_id,
                day_number=day_number,
                time_slot=infer_time_slot(index, total),
                duration_hours=None,
                activity_type=infer_activity_type(cleaned_title or raw_name),
                included=included,
                notes=notes,
            )
        )
    return activities


def build_trip_title(selected_products: List[SelectedProduct], cities: List[str], total_days: int) -> str:
    if len(selected_products) == 1:
        return f"{selected_products[0].product.product_name} Plan"
    city_label = " / ".join(cities) if cities else "Multi-city"
    return f"{city_label} {total_days}-Day Plan"


def assign_day_date(travel_window: TravelWindow, offset_days: int):
    if not travel_window.start_date:
        return None
    return travel_window.start_date + timedelta(days=offset_days)


def build_plan_object(
    lead: Any,
    selected_products: List[SelectedProduct],
    normalized_products: Optional[List[Dict[str, Any]]] = None,
) -> PlanObject:
    normalized_lookup: Dict[str, Dict[str, Any]] = {}
    for product in normalized_products or []:
        product_id = product.get("product_id")
        if product_id:
            normalized_lookup[product_id] = product

    day_plans: List[PlanDay] = []
    planning_notes: List[str] = []
    cities: List[str] = []
    total_days = 0
    date_offset = 0

    for selected_product in selected_products:
        product_ref = selected_product.product
        city = product_ref.city
        if city and city not in cities:
            cities.append(city)

        product_data = normalized_lookup.get(product_ref.product_id, {})
        source_day_plans = product_data.get("day_plans", [])

        if not source_day_plans:
            planning_notes.append(
                f"No structured day_plans found for {product_ref.product_id}; downstream itinerary enrichment may be required."
            )

        total_days += max(product_ref.duration_days, len(source_day_plans), 1)

        for day_index in range(max(len(source_day_plans), product_ref.duration_days or 1)):
            source_day = source_day_plans[day_index] if day_index < len(source_day_plans) else {}
            global_day_number = len(day_plans) + 1
            activity_names = source_day.get("activity_names", []) or []
            if not activity_names and source_day.get("raw_text"):
                activity_names = [source_day.get("raw_text")]

            activities = build_plan_activities_for_day(
                city=city,
                product_id=product_ref.product_id,
                day_number=global_day_number,
                raw_activities=activity_names,
                selected_optional_items=selected_product.selected_optional_items,
            )

            if not activities:
                planning_notes.append(
                    f"Day {global_day_number} of {product_ref.product_id} has no parsed activities; sales should add manual itinerary notes."
                )

            day_plans.append(
                PlanDay(
                    day_number=global_day_number,
                    date=assign_day_date(lead.travel_window, date_offset),
                    city=city,
                    theme=infer_day_theme(activity_names),
                    activities=activities,
                    transport_notes=build_transport_notes(day_index + 1, max(len(source_day_plans), product_ref.duration_days or 1), city),
                    hotel_checkin=True if day_index == 0 and product_ref.duration_days > 1 else None,
                    hotel_checkout=True if day_index == max(len(source_day_plans), product_ref.duration_days or 1) - 1 and product_ref.duration_days > 1 else None,
                )
            )
            date_offset += 1

        if selected_product.custom_adjustments:
            planning_notes.extend(
                [f"{product_ref.product_id} adjustment: {note}" for note in selected_product.custom_adjustments]
            )

    if not selected_products:
        planning_notes.append("No selected products were provided; plan object is structurally valid but empty.")
        total_days = lead.intent.trip_days or 1

    if lead.intent.trip_days and total_days != lead.intent.trip_days:
        planning_notes.append(
            f"Lead requested {lead.intent.trip_days} day(s), while current selected products sum to {total_days} day(s)."
        )

    return PlanObject(
        lead_id=lead.lead_id,
        trip_title=build_trip_title(selected_products, cities, total_days),
        cities=cities,
        total_days=max(total_days, 1),
        travel_window=lead.travel_window,
        selected_products=selected_products,
        day_plans=day_plans,
        planning_notes=planning_notes,
        generated_by="agent_3_plan_structurer",
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
