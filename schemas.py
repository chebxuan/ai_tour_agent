from __future__ import annotations

from datetime import date as dt_date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# Core shared objects
# ============================================================


class PassengerMix(BaseModel):
    adults: int = Field(1, ge=1, description="Number of adult travelers")
    children: int = Field(0, ge=0, description="Number of child travelers")
    seniors: int = Field(0, ge=0, description="Number of senior travelers")


class BudgetPreference(BaseModel):
    tier: Optional[Literal["budget", "standard", "comfort", "premium", "luxury"]] = Field(
        None, description="Budget tier preference"
    )
    max_total: Optional[float] = Field(None, ge=0, description="Max total budget in RMB")
    max_per_person: Optional[float] = Field(None, ge=0, description="Max per-person budget in RMB")
    notes: Optional[str] = Field(None, description="Budget notes from sales or customer")


class HotelPreference(BaseModel):
    tier: Optional[Literal["budget", "standard", "comfort", "premium", "luxury"]] = None
    room_view_priority: bool = Field(False, description="Whether scenic room view is important")
    style_notes: Optional[str] = Field(None, description="Style, location, or other hotel notes")
    special_requirements: List[str] = Field(default_factory=list)


class TravelWindow(BaseModel):
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    flexible_days: Optional[int] = Field(None, ge=0)
    season: Optional[str] = Field(None, description="Natural language season or timing note")


class ContactInfo(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    wechat: Optional[str] = None
    nationality: Optional[str] = None


class ProductReference(BaseModel):
    product_id: str = Field(..., description="Stable product id from product library")
    city: str = Field(..., description="Product city")
    product_name: str = Field(..., description="Display name")
    duration_days: int = Field(..., ge=1)
    daily_itinerary: Optional[str] = Field(None, description="Daily itinerary text from product library")


class MoneyAmount(BaseModel):
    currency: str = Field("RMB")
    amount: float = Field(..., ge=0)


# ============================================================
# 1. Lead JSON
# ============================================================


class LeadIntent(BaseModel):
    destination_cities: List[str] = Field(default_factory=list)
    trip_days: Optional[int] = Field(None, ge=1, description="Requested or inferred trip days")
    interests: List[str] = Field(default_factory=list)
    travel_style: List[str] = Field(default_factory=list)
    must_have: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    departure_city: Optional[str] = None
    transport_preference: Optional[str] = None
    need_guide: Optional[bool] = None
    need_private_car: Optional[bool] = None
    need_airport_transfer: Optional[bool] = None
    dietary_notes: List[str] = Field(default_factory=list)


class LeadSource(BaseModel):
    channel: Optional[str] = Field(None, description="e.g. email, form, whatsapp, sales chat")
    source_id: Optional[str] = Field(None, description="External message/form/thread id")
    raw_text: Optional[str] = Field(None, description="Original inquiry text or merged notes")


class LeadJSON(BaseModel):
    lead_id: str = Field(..., description="Stable internal lead id")
    stage: Literal["lead", "qualified", "quoted", "confirmed"] = "lead"
    contact: ContactInfo = Field(default_factory=ContactInfo)
    travel_window: TravelWindow = Field(default_factory=TravelWindow)
    passenger_mix: PassengerMix = Field(default_factory=PassengerMix)
    budget_preference: BudgetPreference = Field(default_factory=BudgetPreference)
    hotel_preference: HotelPreference = Field(default_factory=HotelPreference)
    intent: LeadIntent = Field(default_factory=LeadIntent)
    sales_notes: List[str] = Field(default_factory=list)
    source: LeadSource = Field(default_factory=LeadSource)
    language: str = Field("en", description="Customer communication language")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================
# 2. Candidate Products JSON
# ============================================================


class ProductCandidateReason(BaseModel):
    matched_interests: List[str] = Field(default_factory=list)
    matched_constraints: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    rationale: str = Field(..., description="Human-readable selection reason")


class ProductCandidate(BaseModel):
    rank: int = Field(..., ge=1)
    product: ProductReference
    match_score: float = Field(..., ge=0, le=1)
    fit_label: Literal["high", "medium", "low"]
    regular_item_codes: List[str] = Field(default_factory=list)
    optional_item_codes: List[str] = Field(default_factory=list)
    reason: ProductCandidateReason


class CandidateProductsJSON(BaseModel):
    lead_id: str
    city_scope: List[str] = Field(default_factory=list)
    query_summary: str = Field(..., description="Short normalized summary of the lead")
    candidates: List[ProductCandidate] = Field(default_factory=list)
    recommended_product_id: Optional[str] = None
    generated_by: str = Field("agent_1_product_matcher")
    generated_at: Optional[str] = None


# ============================================================
# 3. Selected Products JSON
# ============================================================


class SelectedOptionalItem(BaseModel):
    code: str
    name: Optional[str] = None
    reason: Optional[str] = None
    selected: bool = True


class SelectedProduct(BaseModel):
    product: ProductReference
    selection_reason: Optional[str] = None
    regular_item_codes: List[str] = Field(default_factory=list)
    selected_optional_items: List[SelectedOptionalItem] = Field(default_factory=list)
    custom_adjustments: List[str] = Field(default_factory=list)


class SelectedProductsJSON(BaseModel):
    lead_id: str
    selected_products: List[SelectedProduct] = Field(default_factory=list)
    selection_notes: List[str] = Field(default_factory=list)
    generated_at: Optional[str] = None


# ============================================================
# 4. Pricing Result JSON
# ============================================================


class PricingValidationIssue(BaseModel):
    field: str
    code: Optional[str] = None
    codes: List[Any] = Field(default_factory=list)
    message: str
    severity: Literal["warning", "error"] = "error"


class PricingLineItem(BaseModel):
    category: Literal["ticket_activity", "hotel", "transport", "guide", "other"]
    code: Optional[str] = None
    name: str
    unit: Optional[str] = None
    unit_price: float = Field(0, ge=0)
    quantity: float = Field(0, ge=0)
    subtotal: float = Field(0, ge=0)
    notes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PricingSummary(BaseModel):
    city: str
    product_name: str
    days: int = Field(..., ge=1)
    total_people: int = Field(..., ge=1)
    adults: int = Field(..., ge=1)
    children: int = Field(0, ge=0)
    seniors: int = Field(0, ge=0)
    is_peak: bool
    hotel_nights: int = Field(0, ge=0)
    car_days: int = Field(0, ge=0)
    transfer_times: int = Field(0, ge=0)
    grand_total: float = Field(..., ge=0)
    per_person: float = Field(..., ge=0)
    currency: str = Field("RMB")


class PricingResultJSON(BaseModel):
    lead_id: Optional[str] = None
    selected_product_id: Optional[str] = None
    success: bool = True
    summary: Optional[PricingSummary] = None
    line_items: List[PricingLineItem] = Field(default_factory=list)
    category_subtotals: Dict[str, float] = Field(default_factory=dict)
    regular_item_codes: List[str] = Field(default_factory=list)
    selected_optional_item_codes: List[str] = Field(default_factory=list)
    validation_issues: List[PricingValidationIssue] = Field(default_factory=list)
    error: Optional[str] = None
    generated_at: Optional[str] = None


# ============================================================
# 5. Quote Explanation JSON
# ============================================================


class QuoteExplanationBlock(BaseModel):
    title: str
    content: str
    related_codes: List[str] = Field(default_factory=list)


class QuoteExplanationJSON(BaseModel):
    lead_id: Optional[str] = None
    selected_product_id: Optional[str] = None
    customer_facing_title: str
    summary_text: str
    price_statement: str = Field(..., description="e.g. RMB 4,445 per Adult on 4 Pax")
    included_blocks: List[QuoteExplanationBlock] = Field(default_factory=list)
    optional_blocks: List[QuoteExplanationBlock] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generated_by: str = Field("agent_2_pricing_copilot")
    generated_at: Optional[str] = None


# ============================================================
# 6. Plan Object
# ============================================================


class PlanActivity(BaseModel):
    activity_id: str
    city: str
    title: str
    source_product_id: Optional[str] = None
    day_number: int = Field(..., ge=1)
    time_slot: Optional[str] = Field(None, description="morning / afternoon / evening / custom")
    duration_hours: Optional[float] = Field(None, ge=0)
    activity_type: Optional[str] = None
    included: bool = True
    notes: List[str] = Field(default_factory=list)


class PlanDay(BaseModel):
    day_number: int = Field(..., ge=1)
    date: Optional[dt_date] = None
    city: str
    theme: Optional[str] = None
    activities: List[PlanActivity] = Field(default_factory=list)
    transport_notes: List[str] = Field(default_factory=list)
    hotel_checkin: Optional[bool] = None
    hotel_checkout: Optional[bool] = None


class PlanObject(BaseModel):
    lead_id: str
    trip_title: Optional[str] = None
    cities: List[str] = Field(default_factory=list)
    total_days: int = Field(..., ge=1)
    travel_window: TravelWindow = Field(default_factory=TravelWindow)
    selected_products: List[SelectedProduct] = Field(default_factory=list)
    day_plans: List[PlanDay] = Field(default_factory=list)
    planning_notes: List[str] = Field(default_factory=list)
    generated_by: str = Field("agent_3_plan_structurer")
    generated_at: Optional[str] = None


# ============================================================
# 7. Confirmed Client Info JSON
# ============================================================


class PassportInfo(BaseModel):
    passport_name: Optional[str] = None
    passport_number: Optional[str] = None
    expiry_date: Optional[dt_date] = None


class EmergencyContact(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    phone: Optional[str] = None


class TravelerProfile(BaseModel):
    traveler_id: str
    full_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[dt_date] = None
    nationality: Optional[str] = None
    passport: PassportInfo = Field(default_factory=PassportInfo)
    dietary_requirements: List[str] = Field(default_factory=list)
    health_notes: List[str] = Field(default_factory=list)
    roommate_preference: Optional[str] = None
    special_requests: List[str] = Field(default_factory=list)


class ConfirmedClientInfoJSON(BaseModel):
    lead_id: str
    booking_id: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    emergency_contact: EmergencyContact = Field(default_factory=EmergencyContact)
    travelers: List[TravelerProfile] = Field(default_factory=list)
    arrival_notes: List[str] = Field(default_factory=list)
    departure_notes: List[str] = Field(default_factory=list)
    internal_notes: List[str] = Field(default_factory=list)
    generated_at: Optional[str] = None


# ============================================================
# 8. Delivery Draft Object
# ============================================================


class DeliveryContactCard(BaseModel):
    role: str
    name: str
    phone: Optional[str] = None
    wechat: Optional[str] = None
    notes: Optional[str] = None


class DeliveryReminder(BaseModel):
    type: Literal["general", "food", "ticket", "transport", "safety", "religion", "hotel"]
    content: str


class DeliveryRow(BaseModel):
    date_label: str
    time_range: Optional[str] = None
    city: str
    activity_title: str
    activity_description: Optional[str] = None
    location_name: Optional[str] = None
    location_details: Optional[str] = None
    contacts: List[DeliveryContactCard] = Field(default_factory=list)
    reminders: List[DeliveryReminder] = Field(default_factory=list)


class DeliverySection(BaseModel):
    section_type: Literal["cover", "notes", "itinerary_table", "hotel", "contacts", "transport", "custom"]
    title: str
    content: Optional[str] = None
    rows: List[DeliveryRow] = Field(default_factory=list)


class DeliveryDraftObject(BaseModel):
    lead_id: str
    booking_id: Optional[str] = None
    document_title: str
    language: str = Field("en")
    trip_summary: Optional[str] = None
    sections: List[DeliverySection] = Field(default_factory=list)
    global_reminders: List[DeliveryReminder] = Field(default_factory=list)
    generated_by: str = Field("agent_4_delivery_composer")
    generated_at: Optional[str] = None
