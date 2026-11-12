"""Logistics request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.crm.schemas import Currency

Status = Literal[
    "planned", "in_transit", "at_customs", "cleared", "arrived", "delivered", "cancelled"
]
DocType = Literal[
    "bill_of_lading",
    "airway_bill",
    "commercial_invoice",
    "packing_list",
    "certificate_of_origin",
    "customs_declaration",
    "import_permit",
    "insurance",
    "other",
]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ShipmentIn(_In):
    direction: Literal["inbound", "outbound"]
    mode: Literal["road", "air", "sea", "rail", "courier", "multimodal"]
    carrier: str | None = Field(default=None, max_length=200)
    tracking_number: str | None = Field(default=None, max_length=120)
    origin: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    purchase_order_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    etd: date | None = None
    eta: date | None = None
    freight_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    freight_currency: Currency | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _rules(self) -> ShipmentIn:
        if self.etd and self.eta and self.eta < self.etd:
            raise ValueError("The arrival date cannot be before departure.")
        if (self.freight_cost is None) != (self.freight_currency is None):
            raise ValueError("Give both a freight cost and its currency, or neither.")
        if self.direction == "inbound" and self.customer_id:
            raise ValueError("An inbound shipment links to a purchase order, not a customer.")
        if self.direction == "outbound" and self.purchase_order_id:
            raise ValueError("An outbound shipment links to a customer, not a purchase order.")
        return self


class StatusIn(_In):
    status: Status
    occurred_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    customs_entry_number: str | None = Field(default=None, max_length=120)


class DocumentIn(_In):
    doc_type: DocType
    file_id: uuid.UUID
    note: str | None = Field(default=None, max_length=300)


class EventOut(BaseModel):
    status: str
    location: str | None
    note: str | None
    occurred_at: datetime
    recorded_by: str


class DocumentOut(BaseModel):
    id: uuid.UUID
    doc_type: str
    file_id: uuid.UUID
    file_name: str
    note: str | None
    created_at: datetime


class ShipmentOut(BaseModel):
    id: uuid.UUID
    reference: str
    direction: str
    mode: str
    carrier: str | None
    tracking_number: str | None
    origin: str
    destination: str
    purchase_order_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    counterparty: str | None
    status: str
    etd: date | None
    eta: date | None
    freight_cost: Decimal | None
    freight_currency: str | None
    customs_entry_number: str | None
    notes: str | None
    late: bool
    created_at: datetime


class ShipmentDetail(BaseModel):
    shipment: ShipmentOut
    events: list[EventOut]
    documents: list[DocumentOut]


class DeliveryLineIn(_In):
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)


class DeliveryNoteIn(_In):
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    shipment_id: uuid.UUID | None = None
    invoice_id: uuid.UUID | None = None
    delivery_address: str = Field(min_length=5, max_length=1000)
    scheduled_for: date | None = None
    lines: list[DeliveryLineIn] = Field(min_length=1, max_length=200)


class ProofIn(_In):
    """Proof of delivery is what the receiver actually gave: their name, and an
    uploaded signed note or photo where one exists. Nothing is generated."""

    received_by_name: str = Field(min_length=2, max_length=200)
    delivered_at: datetime | None = None
    proof_file_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


class DeliveryLineOut(BaseModel):
    line_no: int
    product_id: uuid.UUID
    sku: str
    product_name: str
    unit: str
    quantity: Decimal


class DeliveryNoteOut(BaseModel):
    id: uuid.UUID
    number: str
    customer_id: uuid.UUID
    customer_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    shipment_id: uuid.UUID | None
    invoice_id: uuid.UUID | None
    delivery_address: str
    scheduled_for: date | None
    status: str
    dispatched_at: datetime | None
    delivered_at: datetime | None
    received_by_name: str | None
    proof_file_id: uuid.UUID | None
    proof_note: str | None
    lines: list[DeliveryLineOut]


class CancelIn(_In):
    reason: str = Field(min_length=3, max_length=2000)


class LogisticsSummary(BaseModel):
    has_records: bool
    active_shipments: int
    late_shipments: int
    at_customs: int
    deliveries_scheduled: int
    awaiting_proof: int
