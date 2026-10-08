from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from backend.app.schemas import (
    CandidateProductsJSON,
    LeadJSON,
    PricingResultJSON,
    RiskCheckResultJSON,
    RiskIssue,
)


def _contains_any(text: str, tokens: List[str]) -> List[str]:
    normalized = text.lower()
    return [token for token in tokens if token and token.lower() in normalized]


def _pricing_has_category(pricing: Optional[PricingResultJSON], category: str) -> bool:
    if not pricing:
        return False
    return any(item.category == category and item.subtotal > 0 for item in pricing.line_items)


def check_workflow_risks(
    lead: LeadJSON,
    product_match: Optional[CandidateProductsJSON] = None,
    pricing: Optional[PricingResultJSON] = None,
    itinerary_markdown: str = "",
) -> RiskCheckResultJSON:
    issues: List[RiskIssue] = []

    if lead.intent.need_private_car is None:
        issues.append(
            RiskIssue(
                severity="warning",
                code="PRIVATE_CAR_NEEDS_CONFIRMATION",
                field="intent.need_private_car",
                message="Private car preference is not confirmed; sales should confirm before final pricing.",
                requires_human_review=True,
            )
        )

    if lead.intent.need_guide and pricing and not _pricing_has_category(pricing, "guide"):
        issues.append(
            RiskIssue(
                severity="blocking",
                code="GUIDE_REQUIRED_BUT_NOT_PRICED",
                field="pricing.line_items",
                message="Customer requires a guide, but no guide cost line item was found in pricing.",
                requires_human_review=True,
            )
        )

    if lead.intent.need_private_car and pricing and pricing.summary and pricing.summary.car_days <= 0:
        issues.append(
            RiskIssue(
                severity="blocking",
                code="PRIVATE_CAR_REQUIRED_BUT_NOT_PRICED",
                field="pricing.summary.car_days",
                message="Customer requires a private car, but pricing has zero car days.",
                requires_human_review=True,
            )
        )

    searchable_text = itinerary_markdown
    if product_match and product_match.candidates:
        top = product_match.candidates[0]
        searchable_text += "\n" + (top.product.product_name or "")
        searchable_text += "\n" + (top.product.daily_itinerary or "")
        searchable_text += "\n" + " ".join(top.reason.warnings)

    avoid_hits = _contains_any(searchable_text, lead.intent.avoid)
    for token in avoid_hits:
        issues.append(
            RiskIssue(
                severity="warning",
                code="AVOID_CONSTRAINT_MAY_BE_TRIGGERED",
                field="intent.avoid",
                message=f"Customer wants to avoid '{token}', but the selected itinerary or product text may contain it.",
                requires_human_review=True,
            )
        )

    if lead.passenger_mix.seniors > 0:
        senior_risk_tokens = ["hiking", "mountain", "long walking", "crowded", "tight schedule", "rushed"]
        senior_hits = _contains_any(searchable_text, senior_risk_tokens)
        if senior_hits:
            issues.append(
                RiskIssue(
                    severity="warning",
                    code="SENIOR_TRAVEL_PACE_RISK",
                    field="passenger_mix.seniors",
                    message=f"Senior traveler detected; review pace and mobility risks: {', '.join(senior_hits)}.",
                    requires_human_review=True,
                )
            )

    human_review_required = any(issue.requires_human_review or issue.severity == "blocking" for issue in issues)

    return RiskCheckResultJSON(
        lead_id=lead.lead_id,
        success=not any(issue.severity == "blocking" for issue in issues),
        issues=issues,
        human_review_required=human_review_required,
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
