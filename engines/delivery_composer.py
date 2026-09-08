from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from schemas import (
    CandidateProductsJSON,
    DeliveryDraftJSON,
    LeadJSON,
    PricingResultJSON,
    RiskCheckResultJSON,
)


def _traveler_label(lead: LeadJSON) -> str:
    pax = lead.passenger_mix
    parts = [f"{pax.adults} adult(s)"]
    if pax.children:
        parts.append(f"{pax.children} child(ren)")
    if pax.seniors:
        parts.append(f"{pax.seniors} senior traveler(s)")
    return ", ".join(parts)


def _destination_label(lead: LeadJSON) -> str:
    return ", ".join(lead.intent.destination_cities) if lead.intent.destination_cities else "your China trip"


def compose_delivery_draft(
    *,
    lead: LeadJSON,
    product_match: Optional[CandidateProductsJSON] = None,
    pricing: Optional[PricingResultJSON] = None,
    risk_check: Optional[RiskCheckResultJSON] = None,
    itinerary_markdown: str = "",
) -> DeliveryDraftJSON:
    top = product_match.candidates[0] if product_match and product_match.candidates else None
    product_name = top.product.product_name if top else "Custom Travel Proposal"
    product_id = top.product.product_id if top else None
    destination = _destination_label(lead)
    days = lead.intent.trip_days or (top.product.duration_days if top else None)

    subject_parts = ["Your"]
    if days:
        subject_parts.append(f"{days}-day")
    subject_parts.append(f"{destination} travel proposal")
    subject = " ".join(subject_parts)

    warnings: List[str] = []
    if risk_check and risk_check.issues:
        warnings = [f"{issue.code}: {issue.message}" for issue in risk_check.issues]

    lines: List[str] = [
        f"Dear Traveler,",
        "",
        f"Thank you for sharing your travel preferences. Based on your request, we prepared an initial proposal for **{destination}**.",
        "",
        "## Trip Summary",
        "",
        f"- Travelers: {_traveler_label(lead)}",
    ]
    if days:
        lines.append(f"- Duration: {days} day(s)")
    if lead.intent.interests:
        lines.append(f"- Interests: {', '.join(lead.intent.interests)}")
    if product_id:
        lines.append(f"- Recommended product: {product_name} ({product_id})")
    elif product_name:
        lines.append(f"- Recommended plan: {product_name}")

    if pricing and pricing.summary:
        lines.extend(
            [
                "",
                "## Estimated Cost",
                "",
                f"- Grand total: RMB {pricing.summary.grand_total:,.2f}",
                f"- Per person: RMB {pricing.summary.per_person:,.2f}",
                f"- Pricing season: {'Peak' if pricing.summary.is_peak else 'Off-peak'}",
            ]
        )

    if warnings:
        lines.extend(
            [
                "",
                "## Items to Confirm",
                "",
            ]
        )
        for warning in warnings:
            lines.append(f"- {warning}")

    if itinerary_markdown:
        lines.extend(
            [
                "",
                "## Draft Itinerary",
                "",
                itinerary_markdown,
            ]
        )

    lines.extend(
        [
            "",
            "Please review this draft and let us know what you would like to adjust. We will confirm final availability and any optional services before issuing the final version.",
            "",
            "Best regards,",
            "",
            "Hexa China Tours",
        ]
    )

    return DeliveryDraftJSON(
        lead_id=lead.lead_id,
        subject=subject,
        body_markdown="\n".join(lines),
        warnings=warnings,
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
