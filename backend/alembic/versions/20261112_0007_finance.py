"""Finance: accounts, periods, exchange rates, tax codes, settings, counters,
journals (with immutability and balance triggers), invoices, receipts,
credit notes, supplier bills, payments and bank-statement lines.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-12

Additive only. No accounts, rates or tax codes are seeded: they are entered
by Finance and reviewed by a qualified accountant. Downgrade drops only the
objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENCY = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"
MONEY = sa.Numeric(18, 2)
RATE = sa.Numeric(18, 6)


def _id() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _ts() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _fk(
    table: str, column: str, target: str, ondelete: str | None = None
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [target],
        name=op.f(f"fk_{table}_{column}_{target.split('.')[0]}"),
        ondelete=ondelete,
    )


def _ck(table: str, name: str, sql: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(sql, name=op.f(f"ck_{table}_{name}"))


def _pk(table: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}"))


def _uq(table: str, *cols: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*cols, name=op.f(f"uq_{table}_{cols[0]}"))


IMMUTABILITY_SQL = """
CREATE FUNCTION fin_guard_journal_entry() RETURNS trigger AS $$
DECLARE
    d numeric;
    c numeric;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status IN ('posted', 'reversed') THEN
            RAISE EXCEPTION 'journal entries must be created unposted';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.status IN ('posted', 'reversed') THEN
            RAISE EXCEPTION 'posted journal entry % cannot be deleted', OLD.number;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.status IN ('posted', 'reversed') THEN
        IF NOT (OLD.status = 'posted' AND NEW.status = 'reversed'
                AND NEW.reversed_by_id IS NOT NULL
                AND (to_jsonb(NEW) - 'status' - 'reversed_by_id' - 'updated_at')
                    = (to_jsonb(OLD) - 'status' - 'reversed_by_id' - 'updated_at')) THEN
            RAISE EXCEPTION 'posted journal entry % cannot be changed; post a reversal', OLD.number;
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.status = 'posted' THEN
        SELECT coalesce(sum(debit), 0), coalesce(sum(credit), 0) INTO d, c
          FROM fin_journal_lines WHERE entry_id = NEW.id;
        IF d <> c OR d <= 0 THEN
            RAISE EXCEPTION 'journal entry does not balance (debits %, credits %)', d, c;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fin_journal_entries_guard
    BEFORE INSERT OR UPDATE OR DELETE ON fin_journal_entries
    FOR EACH ROW EXECUTE FUNCTION fin_guard_journal_entry();

CREATE FUNCTION fin_guard_journal_line() RETURNS trigger AS $$
DECLARE
    s text;
BEGIN
    SELECT status INTO s FROM fin_journal_entries
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
    IF s IN ('posted', 'reversed') THEN
        RAISE EXCEPTION 'lines of a posted journal entry cannot be changed';
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.entry_id <> NEW.entry_id THEN
        RAISE EXCEPTION 'a journal line cannot move to another entry';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fin_journal_lines_guard
    BEFORE INSERT OR UPDATE OR DELETE ON fin_journal_lines
    FOR EACH ROW EXECUTE FUNCTION fin_guard_journal_line();

CREATE FUNCTION fin_guard_issued_document() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.number IS NOT NULL THEN
            RAISE EXCEPTION '% % cannot be deleted', TG_TABLE_NAME, OLD.number;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.status <> 'draft' AND (
        (to_jsonb(NEW) - 'status' - 'amount_paid' - 'amount_credited' - 'updated_at')
        <> (to_jsonb(OLD) - 'status' - 'amount_paid' - 'amount_credited' - 'updated_at')
    ) THEN
        RAISE EXCEPTION '% % is issued; correct it with a credit note', TG_TABLE_NAME, OLD.number;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fin_invoices_guard BEFORE UPDATE OR DELETE ON fin_invoices
    FOR EACH ROW EXECUTE FUNCTION fin_guard_issued_document();
CREATE TRIGGER fin_bills_guard BEFORE UPDATE OR DELETE ON fin_bills
    FOR EACH ROW EXECUTE FUNCTION fin_guard_issued_document();

CREATE FUNCTION fin_guard_document_line() RETURNS trigger AS $$
DECLARE
    s text;
BEGIN
    IF TG_TABLE_NAME = 'fin_invoice_lines' THEN
        SELECT status INTO s FROM fin_invoices
         WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.invoice_id ELSE NEW.invoice_id END;
    ELSE
        SELECT status INTO s FROM fin_bills
         WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.bill_id ELSE NEW.bill_id END;
    END IF;
    IF s IS NOT NULL AND s <> 'draft' THEN
        RAISE EXCEPTION 'lines of an issued document cannot be changed';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fin_invoice_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON fin_invoice_lines
    FOR EACH ROW EXECUTE FUNCTION fin_guard_document_line();
CREATE TRIGGER fin_bill_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON fin_bill_lines
    FOR EACH ROW EXECUTE FUNCTION fin_guard_document_line();

CREATE FUNCTION fin_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fin_receipts_append_only BEFORE UPDATE OR DELETE ON fin_receipts
    FOR EACH ROW EXECUTE FUNCTION fin_append_only();
CREATE TRIGGER fin_receipt_allocations_append_only
    BEFORE UPDATE OR DELETE ON fin_receipt_allocations
    FOR EACH ROW EXECUTE FUNCTION fin_append_only();
CREATE TRIGGER fin_exchange_rates_append_only BEFORE UPDATE OR DELETE ON fin_exchange_rates
    FOR EACH ROW EXECUTE FUNCTION fin_append_only();
"""

DROP_TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS fin_exchange_rates_append_only ON fin_exchange_rates;
DROP TRIGGER IF EXISTS fin_receipt_allocations_append_only ON fin_receipt_allocations;
DROP TRIGGER IF EXISTS fin_receipts_append_only ON fin_receipts;
DROP TRIGGER IF EXISTS fin_bill_lines_guard ON fin_bill_lines;
DROP TRIGGER IF EXISTS fin_invoice_lines_guard ON fin_invoice_lines;
DROP TRIGGER IF EXISTS fin_bills_guard ON fin_bills;
DROP TRIGGER IF EXISTS fin_invoices_guard ON fin_invoices;
DROP TRIGGER IF EXISTS fin_journal_lines_guard ON fin_journal_lines;
DROP TRIGGER IF EXISTS fin_journal_entries_guard ON fin_journal_entries;
DROP FUNCTION IF EXISTS fin_append_only();
DROP FUNCTION IF EXISTS fin_guard_document_line();
DROP FUNCTION IF EXISTS fin_guard_issued_document();
DROP FUNCTION IF EXISTS fin_guard_journal_line();
DROP FUNCTION IF EXISTS fin_guard_journal_entry();
"""


def upgrade() -> None:
    t = "fin_accounts"
    op.create_table(
        t,
        _id(),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("subtype", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "type_valid", "type IN ('asset', 'liability', 'equity', 'income', 'expense')"),
        _ck(t, "currency_valid", "currency IS NULL OR " + CURRENCY),
        _ck(t, "code_format", "code ~ '^[0-9A-Z.\\-]{2,20}$'"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "code"),
    )

    t = "fin_periods"
    op.create_table(
        t,
        _id(),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(8), server_default="open", nullable=False),
        sa.Column("closed_by", sa.Uuid()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_ts(),
        _ck(t, "dates_ordered", "start_date <= end_date"),
        _ck(t, "status_valid", "status IN ('open', 'closed')"),
        _fk(t, "closed_by", "auth_users.id"),
        _pk(t),
        _uq(t, "name"),
    )

    t = "fin_exchange_rates"
    op.create_table(
        t,
        _id(),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("rate", RATE, nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "rate_positive", "rate > 0"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "currency", "rate_date"),
    )

    t = "fin_tax_codes"
    op.create_table(
        t,
        _id(),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("rate_pct", sa.Numeric(7, 3), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "rate_range", "rate_pct >= 0 AND rate_pct <= 100"),
        _ck(t, "kind_valid", "kind IN ('output', 'input')"),
        _ck(t, "dates_ordered", "effective_to IS NULL OR effective_to >= effective_from"),
        _fk(t, "account_id", "fin_accounts.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "code"),
    )

    t = "fin_settings"
    op.create_table(
        t,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receivable_account_id", sa.Uuid()),
        sa.Column("payable_account_id", sa.Uuid()),
        sa.Column("fx_gain_loss_account_id", sa.Uuid()),
        sa.Column(
            "accountant_reviewed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("updated_by", sa.Uuid()),
        *_ts(),
        _ck(t, "single_row", "id = 1"),
        _fk(t, "receivable_account_id", "fin_accounts.id"),
        _fk(t, "payable_account_id", "fin_accounts.id"),
        _fk(t, "fx_gain_loss_account_id", "fin_accounts.id"),
        _fk(t, "updated_by", "auth_users.id"),
        _pk(t),
    )

    op.create_table(
        "fin_counters",
        sa.Column("key", sa.String(30), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_fin_counters")),
    )

    t = "fin_journal_entries"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24)),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("period_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("source_type", sa.String(12), nullable=False),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("reverses_id", sa.Uuid()),
        sa.Column("reversed_by_id", sa.Uuid()),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("posted_by", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(
            t,
            "status_valid",
            "status IN ('draft', 'awaiting_approval', 'posted', 'reversed', 'rejected')",
        ),
        _ck(
            t,
            "source_valid",
            "source_type IN ('manual', 'invoice', 'receipt', 'credit_note', 'bill', 'payment', "
            "'reversal')",
        ),
        _ck(
            t,
            "posted_has_number",
            "status NOT IN ('posted', 'reversed') "
            "OR (number IS NOT NULL AND posted_at IS NOT NULL)",
        ),
        _fk(t, "period_id", "fin_periods.id"),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "reverses_id", "fin_journal_entries.id"),
        _fk(t, "posted_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
    )
    op.create_index("ix_fin_journal_entries_date", t, ["entry_date"])

    t = "fin_journal_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(300)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("fx_rate", RATE, nullable=False),
        sa.Column("debit", MONEY, server_default="0", nullable=False),
        sa.Column("credit", MONEY, server_default="0", nullable=False),
        sa.Column("party_type", sa.String(10)),
        sa.Column("party_id", sa.Uuid()),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "non_negative", "amount >= 0 AND debit >= 0 AND credit >= 0"),
        _ck(t, "debit_xor_credit", "(debit = 0) <> (credit = 0)"),
        _ck(t, "rate_positive", "fx_rate > 0"),
        _ck(t, "party_valid", "party_type IS NULL OR party_type IN ('customer', 'supplier')"),
        _fk(t, "entry_id", "fin_journal_entries.id"),
        _fk(t, "account_id", "fin_accounts.id"),
        _pk(t),
        _uq(t, "entry_id", "line_no"),
    )
    op.create_index(op.f("ix_fin_journal_lines_entry_id"), t, ["entry_id"])
    op.create_index("ix_fin_journal_lines_account", t, ["account_id"])

    t = "fin_invoices"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24)),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", RATE),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("subtotal", MONEY, server_default="0", nullable=False),
        sa.Column("tax_total", MONEY, server_default="0", nullable=False),
        sa.Column("total", MONEY, server_default="0", nullable=False),
        sa.Column("amount_paid", MONEY, server_default="0", nullable=False),
        sa.Column("amount_credited", MONEY, server_default="0", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("journal_id", sa.Uuid()),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("issued_by", sa.Uuid()),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "currency_valid", CURRENCY),
        _ck(
            t,
            "status_valid",
            "status IN ('draft', 'issued', 'partially_paid', 'paid', 'credited')",
        ),
        _ck(t, "due_after_issue", "due_date >= issue_date"),
        _ck(
            t,
            "settlement_within_total",
            "amount_paid >= 0 AND amount_credited >= 0 AND amount_paid + amount_credited <= total",
        ),
        _fk(t, "customer_id", "crm_customers.id"),
        _fk(t, "journal_id", "fin_journal_entries.id"),
        _fk(t, "opportunity_id", "crm_opportunities.id"),
        _fk(t, "issued_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
    )

    t = "fin_invoice_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("tax_code_id", sa.Uuid()),
        sa.Column("net", MONEY, nullable=False),
        sa.Column("tax", MONEY, nullable=False),
        _ck(t, "amounts_valid", "quantity > 0 AND unit_price >= 0"),
        _fk(t, "invoice_id", "fin_invoices.id", "CASCADE"),
        _fk(t, "account_id", "fin_accounts.id"),
        _fk(t, "tax_code_id", "fin_tax_codes.id"),
        _pk(t),
        _uq(t, "invoice_id", "line_no"),
    )
    op.create_index(op.f("ix_fin_invoice_lines_invoice_id"), t, ["invoice_id"])

    t = "fin_receipts"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", RATE, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("bank_account_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "amount_positive", "amount > 0"),
        _fk(t, "customer_id", "crm_customers.id"),
        _fk(t, "bank_account_id", "fin_accounts.id"),
        _fk(t, "journal_id", "fin_journal_entries.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
    )

    t = "fin_receipt_allocations"
    op.create_table(
        t,
        _id(),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        _ck(t, "amount_positive", "amount > 0"),
        _fk(t, "receipt_id", "fin_receipts.id"),
        _fk(t, "invoice_id", "fin_invoices.id"),
        _pk(t),
    )
    op.create_index(op.f("ix_fin_receipt_allocations_receipt_id"), t, ["receipt_id"])
    op.create_index(op.f("ix_fin_receipt_allocations_invoice_id"), t, ["invoice_id"])

    t = "fin_credit_notes"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24)),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("credit_date", sa.Date(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="awaiting_approval", nullable=False),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("journal_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('awaiting_approval', 'posted', 'rejected')"),
        _ck(t, "amount_positive", "amount > 0"),
        _ck(t, "posted_has_number", "status <> 'posted' OR number IS NOT NULL"),
        _fk(t, "invoice_id", "fin_invoices.id"),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "journal_id", "fin_journal_entries.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
    )

    t = "fin_bills"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24)),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_invoice_ref", sa.String(120), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid()),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", RATE),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("subtotal", MONEY, server_default="0", nullable=False),
        sa.Column("tax_total", MONEY, server_default="0", nullable=False),
        sa.Column("total", MONEY, server_default="0", nullable=False),
        sa.Column("amount_paid", MONEY, server_default="0", nullable=False),
        sa.Column("journal_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "status_valid", "status IN ('draft', 'posted', 'partially_paid', 'paid')"),
        _ck(t, "due_after_bill", "due_date >= bill_date"),
        _ck(t, "paid_within_total", "amount_paid >= 0 AND amount_paid <= total"),
        _fk(t, "supplier_id", "prc_suppliers.id"),
        _fk(t, "purchase_order_id", "prc_purchase_orders.id"),
        _fk(t, "journal_id", "fin_journal_entries.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
        _uq(t, "supplier_id", "supplier_invoice_ref"),
    )

    t = "fin_bill_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("bill_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("tax_code_id", sa.Uuid()),
        sa.Column("net", MONEY, nullable=False),
        sa.Column("tax", MONEY, nullable=False),
        _ck(t, "amounts_valid", "quantity > 0 AND unit_price >= 0"),
        _fk(t, "bill_id", "fin_bills.id", "CASCADE"),
        _fk(t, "account_id", "fin_accounts.id"),
        _fk(t, "tax_code_id", "fin_tax_codes.id"),
        _pk(t),
        _uq(t, "bill_id", "line_no"),
    )
    op.create_index(op.f("ix_fin_bill_lines_bill_id"), t, ["bill_id"])

    t = "fin_payments"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24)),
        sa.Column("bill_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_bank_account_id", sa.Uuid()),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", RATE, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("bank_account_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("status", sa.String(20), server_default="awaiting_approval", nullable=False),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("journal_id", sa.Uuid()),
        sa.Column("prepared_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "amount_positive", "amount > 0"),
        _ck(t, "status_valid", "status IN ('awaiting_approval', 'posted', 'rejected')"),
        _ck(t, "posted_has_number", "status <> 'posted' OR number IS NOT NULL"),
        _fk(t, "bill_id", "fin_bills.id"),
        _fk(t, "supplier_id", "prc_suppliers.id"),
        _fk(t, "supplier_bank_account_id", "prc_supplier_bank_accounts.id"),
        _fk(t, "bank_account_id", "fin_accounts.id"),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "journal_id", "fin_journal_entries.id"),
        _fk(t, "prepared_by", "auth_users.id"),
        _pk(t),
        _uq(t, "number"),
    )

    t = "fin_bank_statement_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("bank_account_id", sa.Uuid(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("matched_line_id", sa.Uuid()),
        sa.Column("matched_by", sa.Uuid()),
        sa.Column("matched_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "amount_non_zero", "amount <> 0"),
        _fk(t, "bank_account_id", "fin_accounts.id"),
        _fk(t, "matched_line_id", "fin_journal_lines.id"),
        _fk(t, "matched_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "matched_line_id"),
    )
    op.create_index(op.f("ix_fin_bank_statement_lines_bank_account_id"), t, ["bank_account_id"])

    op.execute(IMMUTABILITY_SQL)


def downgrade() -> None:
    op.execute(DROP_TRIGGERS_SQL)
    for table in (
        "fin_bank_statement_lines",
        "fin_payments",
        "fin_bill_lines",
        "fin_bills",
        "fin_credit_notes",
        "fin_receipt_allocations",
        "fin_receipts",
        "fin_invoice_lines",
        "fin_invoices",
        "fin_journal_lines",
        "fin_journal_entries",
        "fin_counters",
        "fin_settings",
        "fin_tax_codes",
        "fin_exchange_rates",
        "fin_periods",
        "fin_accounts",
    ):
        op.drop_table(table)
