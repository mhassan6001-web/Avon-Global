"""Human-readable document references (``PREFIX-00001``) from PostgreSQL sequences.

Sequences never repeat a value, so references are unique even under concurrent
inserts. Gaps are possible (a rolled-back transaction consumes a number); where
gap-free numbering is a legal requirement (invoices, receipts) Finance uses its
own locked counters instead.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Allow-list: only these sequence names may be used (they are interpolated into SQL).
SEQUENCES: dict[str, str] = {
    "CUS": "crm_customer_ref_seq",
    "OPP": "crm_opportunity_ref_seq",
    "TND": "tnd_tender_ref_seq",
    "SUP": "prc_supplier_ref_seq",
    "PR": "prc_request_ref_seq",
    "PO": "prc_order_ref_seq",
    "GRN": "inv_grn_ref_seq",
    "SHP": "lgx_shipment_ref_seq",
    "DN": "lgx_delivery_ref_seq",
}


def next_reference(db: Session, prefix: str) -> str:
    sequence = SEQUENCES[prefix]
    value = db.execute(text(f"SELECT nextval('{sequence}')")).scalar_one()  # nosec B608
    return f"{prefix}-{int(value):05d}"
