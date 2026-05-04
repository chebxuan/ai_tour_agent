from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from schemas import (
    ConfirmedClientInfoJSON,
    DeliveryContactCard,
    DeliveryDraftObject,
    DeliveryReminder,
    DeliveryRow,
    DeliverySection,
    PlanActivity,
    PlanDay,
    PlanObject,
)


def build_document_title(trip_title: Optional[str]) -> str:
    base = (trip_title or "Trip").strip()
    return f"{base} — Delivery Brief"


def build_trip_summary(plan: PlanObject) -> str:
    cities = ", ".join(plan.cities) if plan.cities else "destination TBD"
    days = f"{plan.total_days}-day" if plan.total_days else "multi-day"
    return f"A {days} journey in {cities}." if plan.cities else f"A {days} journey."


def format_date_label(day: PlanDay) -> str:
    if day.date:
        return str(day.date)
    return f"Day {day.day_number}"


def map_time_slot(slot: Optional[str]) -> Optional[str]:
    if not slot:
        return None
    mapping = {
        "morning": "🌅 Morning",
        "afternoon": "☀️ Afternoon",
        "evening": "🌙 Evening",
        "custom": None,
    }
    return mapping.get(slot.lower(), slot)


def build_reminders_from_notes(notes: List[str]) -> List[DeliveryReminder]:
    reminders: List[DeliveryReminder] = []
    for note in notes:
        lower = note.lower()
        if any(keyword in lower for keyword in ["passport", "ticket", "id"]):
            reminders.append(DeliveryReminder(type="ticket", content=note))
        elif any(keyword in lower for keyword in ["food", "meal", "dietary"]):
            reminders.append(DeliveryReminder(type="food", content=note))
        elif any(keyword in lower for keyword in ["transfer", "pickup", "airport", "train"]):
            reminders.append(DeliveryReminder(type="transport", content=note))
        elif any(keyword in lower for keyword in ["safety", "secure", "valuables"]):
            reminders.append(DeliveryReminder(type="safety", content=note))
        else:
            reminders.append(DeliveryReminder(type="general", content=note))
    return reminders


def build_delivery_row_from_activity(activity: PlanActivity, day: PlanDay) -> DeliveryRow:
    return DeliveryRow(
        date_label=format_date_label(day),
        time_range=map_time_slot(activity.time_slot),
        city=activity.city,
        activity_title=activity.title,
        activity_description=None,
        location_name=None,
        location_details=None,
        contacts=[],
        reminders=build_reminders_from_notes(activity.notes or []),
    )


def build_itinerary_section(day_plans: List[PlanDay]) -> DeliverySection:
    rows: List[DeliveryRow] = []
    for day in day_plans:
        for activity in day.activities:
            rows.append(build_delivery_row_from_activity(activity, day))
    return DeliverySection(
        section_type="itinerary_table",
        title="Day-by-Day Itinerary",
        content=None,
        rows=rows,
    )


def build_cover_section(plan: PlanObject, has_client_info: bool) -> DeliverySection:
    notes: List[str] = []
    if not has_client_info:
        notes.append("Client confirmation details are not yet provided.")
    content = f"This delivery draft is based on the confirmed plan. { ' '.join(notes) }".strip()
    return DeliverySection(
        section_type="cover",
        title="Trip Overview",
        content=content,
        rows=[],
    )


def build_notes_section(plan: PlanObject, client_info: Optional[ConfirmedClientInfoJSON]) -> DeliverySection:
    notes: List[str] = []
    notes.append("Please carry your passport for attraction entry where required.")
    notes.append("Meals are not included unless specified.")
    notes.append("Tipping is not mandatory but appreciated for good service.")
    if plan.planning_notes:
        notes.extend(plan.planning_notes[:3])
    if client_info:
        dietary = [t.dietary_requirements for t in client_info.travelers if t.dietary_requirements]
        health = [t.health_notes for t in client_info.travelers if t.health_notes]
        if dietary:
            notes.append(f"Dietary notes: {', '.join([item for sublist in dietary for item in sublist])}.")
        if health:
            notes.append(f"Health notes: {', '.join([item for sublist in health for item in sublist])}.")
    return DeliverySection(
        section_type="notes",
        title="Important Notes",
        content="\n".join([f"- {n}" for n in notes]),
        rows=[],
    )


def build_hotel_section(plan: PlanObject) -> DeliverySection:
    total_days = plan.total_days or 1
    nights = max(total_days - 1, 0)
    cities_str = ", ".join(plan.cities) if plan.cities else "your destination"
    if nights > 0:
        content = (
            f"{nights} night(s) accommodation in {cities_str}. "
            f"Specific hotel names to be confirmed by operations. "
            f"We typically select hotels with good location, comfortable rooms, and friendly service."
        )
    else:
        content = "Day trip — no overnight accommodation required."
    return DeliverySection(
        section_type="hotel",
        title="Hotel Stays",
        content=content,
        rows=[],
    )


def build_transport_section(plan: PlanObject) -> DeliverySection:
    transport_notes: List[str] = []
    for day in plan.day_plans:
        for note in (day.transport_notes or []):
            transport_notes.append(note)
    if transport_notes:
        lines = ["Transport arrangements for this trip:"]
        for note in transport_notes[:5]:
            lines.append(f"- {note}")
        content = "\n".join(lines)
    else:
        content = "Transport arrangements to be confirmed. We will arrange private transfers or provide guidance based on your preference."
    return DeliverySection(
        section_type="transport",
        title="Transport Arrangements",
        content=content,
        rows=[],
    )


def build_contacts_section(plan: PlanObject, client_info: Optional[ConfirmedClientInfoJSON] = None) -> DeliverySection:
    rows: List[DeliveryRow] = []
    cities_seen: set = set()

    # Per-city local company contacts from plan
    for day in plan.day_plans:
        city = day.city
        if city and city not in cities_seen:
            cities_seen.add(city)
            contact_card = DeliveryContactCard(
                role="Local Company",
                name=f"Hexa China Tours — {city} Office",
                phone="TBD",
                notes=f"Local contact for {city}",
            )
            rows.append(
                DeliveryRow(
                    date_label="",
                    time_range=None,
                    city=city,
                    activity_title=f"Local Contact — {city}",
                    activity_description=f"Your local company contact for {city}. Contact details will be provided closer to the travel date.",
                    location_name=None,
                    location_details=None,
                    contacts=[contact_card],
                    reminders=[],
                )
            )

    # Emergency contact from client info (if provided)
    emergency_contacts: List[DeliveryContactCard] = []
    if client_info and client_info.emergency_contact:
        emergency_contacts.append(
            DeliveryContactCard(
                role="Emergency Contact",
                name=client_info.emergency_contact.name or "TBD",
                phone=client_info.emergency_contact.phone,
                notes=client_info.emergency_contact.relationship,
            )
        )
    if emergency_contacts:
        rows.append(
            DeliveryRow(
                date_label="",
                time_range=None,
                city="",
                activity_title="Emergency Contact",
                activity_description=None,
                location_name=None,
                location_details=None,
                contacts=emergency_contacts,
                reminders=[],
            )
        )

    return DeliverySection(
        section_type="contacts",
        title="Key Contacts",
        content="Your local company will assist you during the trip. Contact details will be confirmed before departure.",
        rows=rows,
    )


def build_global_reminders() -> List[DeliveryReminder]:
    return [
        DeliveryReminder(type="safety", content="Keep valuables secure in crowded areas."),
        DeliveryReminder(type="general", content="Carry a printed copy of your passport and visa."),
    ]


def build_delivery_draft(
    plan: PlanObject,
    confirmed_client_info: Optional[ConfirmedClientInfoJSON] = None,
    language: str = "en",
) -> DeliveryDraftObject:
    has_client_info = confirmed_client_info is not None
    sections: List[DeliverySection] = [
        build_cover_section(plan, has_client_info),
        build_itinerary_section(plan.day_plans),
        build_hotel_section(plan),
        build_transport_section(plan),
        build_contacts_section(plan, confirmed_client_info),
        build_notes_section(plan, confirmed_client_info),
    ]
    return DeliveryDraftObject(
        lead_id=plan.lead_id,
        booking_id=None,
        document_title=build_document_title(plan.trip_title),
        language=language,
        trip_summary=build_trip_summary(plan),
        sections=sections,
        global_reminders=build_global_reminders(),
        generated_by="agent_4_delivery_composer",
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
