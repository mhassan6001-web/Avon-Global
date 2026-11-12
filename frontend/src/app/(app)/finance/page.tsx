"use client";

import Link from "next/link";
import { LuBanknote, LuFileText, LuHandCoins, LuReceipt } from "react-icons/lu";

import { BarChart, ChartCard, KpiCard } from "@/components/charts/Charts";
import { FinanceNav } from "@/components/finance/FinanceNav";
import { Badge, FormError, PageHeader, Panel } from "@/components/ui";
import { useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatMoney } from "@/lib/crm/types";
import type { Overview, Settings } from "@/lib/finance/types";

import page from "@/app/pages.module.css";

export default function FinanceOverviewPage() {
  const { can } = useAuth();
  const settings = useResource<Settings>("/finance/settings");
  const overview = useResource<Overview>(can("finance.ledger.view") ? "/finance/overview" : null);
  const o = overview.data;
  const ccy = o?.functional_currency ?? "MWK";
  const value = (amount: string | undefined) =>
    o?.has_records && amount !== undefined ? formatMoney(amount, ccy) : null;

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Finance"
        description="Double-entry books. Posted records are never edited: corrections are reversals and credit notes. Restricted transactions are approved by a different person."
        actions={
          settings.data ? (
            <Badge tone={settings.data.accountant_reviewed ? "success" : "warning"}>
              {settings.data.accountant_reviewed
                ? "Accountant reviewed"
                : "Not yet reviewed by an accountant"}
            </Badge>
          ) : undefined
        }
      />
      <FinanceNav />
      <FormError message={settings.error ?? overview.error} />
      {settings.data && settings.data.missing.length > 0 && (
        <div className={page.notice} role="status" style={{ marginBottom: 20 }}>
          <strong>Setup needed before posting:</strong> {settings.data.missing.join(", ")}.{" "}
          <Link href="/finance/settings" className={page.inlineLink}>
            Open setup
          </Link>
        </div>
      )}
      <div className={page.grid}>
        <div className={page.span6}>
          <KpiCard
            icon={<LuBanknote />}
            label={`Cash position (${ccy})`}
            value={value(o?.cash_position)}
            note="Bank and cash accounts, posted records"
          />
        </div>
        <div className={page.span6}>
          <KpiCard
            icon={<LuFileText />}
            label="Revenue invoiced this month"
            value={value(o?.invoiced_this_month)}
            note="Excluding tax. Not cash."
          />
        </div>
        <div className={page.span6}>
          <KpiCard
            icon={<LuHandCoins />}
            label="Cash collected this month"
            value={value(o?.collected_this_month)}
            note="Receipts posted"
          />
        </div>
        <div className={page.span6}>
          <KpiCard
            icon={<LuReceipt />}
            label="Debtors / creditors"
            value={
              o?.has_records
                ? `${formatMoney(o.debtors_outstanding, ccy)} / ${formatMoney(o.creditors_outstanding, ccy)}`
                : null
            }
          />
        </div>
        <div className={page.span12}>
          <ChartCard
            title="Revenue invoiced vs cash collected"
            meta={`Last 12 months · ${ccy}`}
            empty={!o?.has_records}
          >
            <BarChart
              data={
                o?.has_records
                  ? o.months.map((m) => ({ label: m.month.slice(5), value: Number(m.invoiced) }))
                  : null
              }
              currency={ccy}
            />
            {o?.has_records && (
              <BarChart
                data={o.months.map((m) => ({
                  label: m.month.slice(5),
                  value: Number(m.collected),
                }))}
                currency={ccy}
                height={90}
              />
            )}
          </ChartCard>
        </div>
        <div className={page.span12}>
          <Panel title="Notes">
            <p className="serif-text">
              Figures come only from posted journals. Revenue invoiced and cash collected are shown
              separately. Tax codes, rates and control accounts are configuration that a qualified
              local accountant must review before live use.
            </p>
          </Panel>
        </div>
      </div>
    </>
  );
}
