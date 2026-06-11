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
# 3. Pricing Result JSON
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
# 4. Supplier Payment Tracker (Kanban)
# ============================================================


class PaymentCostItem(BaseModel):
    item_name: str = Field(..., description="Cost item name, e.g. 导游费用")
    item_code: Optional[str] = Field(None, description="Item code from mashes, e.g. BJ-GUIDE-01")
    amount: float = Field(..., ge=0, description="Amount in RMB for this line item")
    invoice_source: Optional[str] = Field(None, description="Who provides the invoice")


class PaymentEntry(BaseModel):
    payment_id: str = Field(..., description="Unique payment identifier, e.g. PAY-001")
    booking_id: Optional[str] = Field(None, description="Related booking ID, e.g. BOOK-001")
    supplier_name: str = Field(..., description="Supplier/partner name")
    related_customer_order: Optional[str] = Field(None, description="Customer-facing order reference")
    status: Literal["pending", "paid", "archived"] = Field("pending", description="Payment status")
    cost_items: List[PaymentCostItem] = Field(default_factory=list)
    total_amount: float = Field(..., ge=0, description="Total payment amount")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
    actual_payment_date: Optional[str] = Field(None, description="Date payment was actually made")
    receipt_link: Optional[str] = Field(None, description="URL to receipt/invoice document")
    notes: Optional[str] = Field(None, description="Free-text notes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last-updated timestamp")


class PaymentCreateRequest(BaseModel):
    booking_id: Optional[str] = None
    supplier_name: str = Field(..., min_length=1)
    related_customer_order: Optional[str] = None
    cost_items: List[PaymentCostItem] = Field(default_factory=list)
    total_amount: float = Field(0, ge=0)
    due_date: Optional[str] = None
    receipt_link: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdateRequest(BaseModel):
    booking_id: Optional[str] = None
    supplier_name: Optional[str] = None
    related_customer_order: Optional[str] = None
    cost_items: Optional[List[PaymentCostItem]] = None
    total_amount: Optional[float] = Field(None, ge=0)
    due_date: Optional[str] = None
    actual_payment_date: Optional[str] = None
    receipt_link: Optional[str] = None
    notes: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    status: Literal["pending", "paid", "archived"]


class PaymentListResponse(BaseModel):
    success: bool
    payments: List[PaymentEntry] = Field(default_factory=list)
    total_count: int = 0
    stats: Optional[Dict[str, Any]] = Field(None, description="Aggregate statistics")
    error: Optional[str] = None


class PaymentDetailResponse(BaseModel):
    success: bool
    payment: Optional[PaymentEntry] = None
    error: Optional[str] = None


class PaymentSuppliersResponse(BaseModel):
    success: bool
    suppliers: List[str] = Field(default_factory=list)
    cost_items: List[Dict[str, str]] = Field(default_factory=list, description="List of {code, name} pairs")
    error: Optional[str] = None


class PaymentStatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
