/** Inventory and logistics types (mirror backend schemas). Quantities stay decimal strings. */

export interface Product {
  id: string;
  sku: string;
  name: string;
  unit: string;
  category: string | null;
  reorder_level: string;
  is_active: boolean;
  on_hand: string;
  value: string;
  below_reorder: boolean;
}

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  location: string | null;
}

export interface Level {
  product_id: string;
  sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_code: string;
  quantity: string;
  average_cost: string;
  value: string;
}

export interface Movement {
  id: string;
  sku: string;
  warehouse_code: string;
  movement_date: string;
  kind: string;
  quantity: string;
  unit_cost: string;
  reference: string | null;
  reason: string | null;
}

export interface OpenOrder {
  id: string;
  reference: string;
  supplier: string;
  lines: Array<{
    line_no: number;
    description: string;
    unit: string;
    ordered: string;
    received: string;
  }>;
}

export interface Shipment {
  id: string;
  reference: string;
  direction: "inbound" | "outbound";
  mode: string;
  carrier: string | null;
  tracking_number: string | null;
  origin: string;
  destination: string;
  counterparty: string | null;
  status: string;
  etd: string | null;
  eta: string | null;
  freight_cost: string | null;
  freight_currency: string | null;
  customs_entry_number: string | null;
  late: boolean;
}

export interface ShipmentDetail {
  shipment: Shipment;
  events: Array<{
    status: string;
    location: string | null;
    note: string | null;
    occurred_at: string;
    recorded_by: string;
  }>;
  documents: Array<{ id: string; doc_type: string; file_name: string; note: string | null }>;
}

export interface DeliveryNote {
  id: string;
  number: string;
  customer_name: string;
  warehouse_code: string;
  delivery_address: string;
  scheduled_for: string | null;
  status: "draft" | "dispatched" | "delivered" | "cancelled";
  dispatched_at: string | null;
  delivered_at: string | null;
  received_by_name: string | null;
  proof_file_id: string | null;
  lines: Array<{
    line_no: number;
    sku: string;
    product_name: string;
    unit: string;
    quantity: string;
  }>;
}

export const SHIPMENT_STATUSES = [
  "planned",
  "in_transit",
  "at_customs",
  "cleared",
  "arrived",
  "delivered",
  "cancelled",
] as const;
export const DOC_TYPES = [
  "bill_of_lading",
  "airway_bill",
  "commercial_invoice",
  "packing_list",
  "certificate_of_origin",
  "customs_declaration",
  "import_permit",
  "insurance",
  "other",
] as const;

export const label = (value: string) =>
  value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

/** Remaining quantity on an order line, as a decimal string with 3 places. */
export function remaining(ordered: string, received: string): string {
  const toMilli = (v: string) => {
    const [w = "0", f = ""] = v.split(".");
    return BigInt(w) * 1000n + BigInt((f + "000").slice(0, 3));
  };
  const left = toMilli(ordered) - toMilli(received);
  const safe = left < 0n ? 0n : left;
  return `${safe / 1000n}.${String(safe % 1000n).padStart(3, "0")}`;
}

/** Trim trailing zeros for display: "5.000" → "5", "2.500" → "2.5". */
export function qty(value: string): string {
  return value.includes(".") ? value.replace(/\.?0+$/, "") : value;
}
