import { LuFileDown } from "react-icons/lu";

import { API_PREFIX } from "@/lib/api/client";

import styles from "./documents.module.css";

type SalesKind = "quotation" | "invoice" | "receipt";
type SupplyKind = "rfq" | "purchase_order" | "delivery_note";
export type RecordKind = SalesKind | SupplyKind;

/**
 * Download links for a record's branded document (PDF / Word). The server
 * checks permission, builds the file from the stored record and registers the version.
 */
export function DocLinks({ kind, id, label }: { kind: RecordKind; id: string; label: string }) {
  const base = `${API_PREFIX}/documents/records/${kind}/${id}`;
  return (
    <span className={styles.links}>
      <LuFileDown aria-hidden="true" />
      <a href={`${base}?format=pdf`} download aria-label={`${label} as PDF`}>
        PDF
      </a>
      <a href={`${base}?format=docx`} download aria-label={`${label} as Word`}>
        Word
      </a>
    </span>
  );
}
