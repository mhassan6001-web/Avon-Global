"use client";

import Link from "next/link";

import { DocLinks } from "@/components/documents/DocLinks";
import styles from "@/components/crm/crm.module.css";
import { ProcurementNav } from "@/components/procurement/ProcurementNav";
import { Badge, EmptyState, FormError, PageHeader, Panel } from "@/components/ui";
import { useResource } from "@/lib/api/useResource";
import { formatDate, formatMoney } from "@/lib/crm/types";
import type { PurchaseOrder } from "@/lib/procurement/types";

import page from "@/app/pages.module.css";

export default function OrdersPage() {
  const { data, error } = useResource<PurchaseOrder[]>("/procurement/orders?limit=200");
  return (
    <>
      <PageHeader
        eyebrow="Procurement"
        title="Purchase orders"
        description="Issued only from Director-approved purchase requests. Goods are received against orders in Inventory."
      />
      <ProcurementNav />
      <Panel title="Orders">
        <FormError message={error} />
        {data && data.length === 0 ? (
          <EmptyState title="No purchase orders yet">
            Orders appear once an approved request is issued.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Order</th>
                  <th scope="col">Supplier</th>
                  <th scope="col">Total</th>
                  <th scope="col">Issued</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((o) => (
                  <tr key={o.id}>
                    <td>
                      <strong>{o.reference}</strong>
                      <DocLinks
                        kind="purchase_order"
                        id={o.id}
                        label={`Purchase order ${o.reference}`}
                      />
                      <div className={styles.ref}>
                        from{" "}
                        <Link
                          href={`/procurement/requests/${o.request_id}`}
                          className={styles.rowLink}
                        >
                          {o.request_reference}
                        </Link>
                      </div>
                    </td>
                    <td>{o.supplier_name}</td>
                    <td className={styles.amount}>{formatMoney(o.total_amount, o.currency)}</td>
                    <td>
                      {formatDate(o.created_at)}
                      {o.issued_by && ` · ${o.issued_by.display_name}`}
                    </td>
                    <td>
                      <Badge
                        tone={
                          o.status === "received"
                            ? "success"
                            : o.status === "cancelled"
                              ? "neutral"
                              : "gold"
                        }
                      >
                        {o.status.replace("_", " ")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
