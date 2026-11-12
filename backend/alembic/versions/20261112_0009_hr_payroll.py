"""HR and payroll: employees, pay history, contracts, leave, attendance,
configured pay components (no built-in rates), commissions, payroll runs
and payslips (frozen once approved), KPIs and reviews.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(18, 2)
CURRENCY = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"
PERIOD = "period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'"


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


def _created() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _fk(t: str, c: str, target: str, ondelete: str | None = None) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [c], [target], name=op.f(f"fk_{t}_{c}_{target.split('.')[0]}"), ondelete=ondelete
    )


def _ck(t: str, n: str, sql: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(sql, name=op.f(f"ck_{t}_{n}"))


def _pk(t: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}"))


def _uq(t: str, *cols: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*cols, name=op.f(f"uq_{t}_{cols[0]}"))


FREEZE_SQL = """
CREATE FUNCTION hr_guard_approved_run() RETURNS trigger AS $$
DECLARE
    s text;
BEGIN
    IF TG_TABLE_NAME = 'hr_payroll_runs' THEN
        IF TG_OP = 'DELETE' THEN
            s := OLD.status;
        ELSE
            s := OLD.status;
        END IF;
    ELSE
        SELECT status INTO s FROM hr_payroll_runs
         WHERE id = CASE WHEN TG_OP = 'INSERT' THEN NEW.run_id ELSE OLD.run_id END;
    END IF;
    IF s = 'approved' THEN
        RAISE EXCEPTION 'an approved payroll run cannot be changed';
    END IF;
    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER hr_payroll_runs_frozen BEFORE UPDATE OR DELETE ON hr_payroll_runs
    FOR EACH ROW EXECUTE FUNCTION hr_guard_approved_run();
CREATE TRIGGER hr_payslips_frozen BEFORE INSERT OR UPDATE OR DELETE ON hr_payslips
    FOR EACH ROW EXECUTE FUNCTION hr_guard_approved_run();

CREATE FUNCTION hr_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is a history table; add a new row instead', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER hr_compensation_append_only BEFORE UPDATE OR DELETE ON hr_compensation
    FOR EACH ROW EXECUTE FUNCTION hr_append_only();
"""


def upgrade() -> None:
    op.execute("CREATE SEQUENCE hr_employee_ref_seq START 1")

    t = "hr_employees"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_no", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("job_title", sa.String(120), nullable=False),
        sa.Column("department_code", sa.String(40), nullable=False),
        sa.Column("employment_type", sa.String(12), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("status", sa.String(10), server_default="active", nullable=False),
        sa.Column("work_email", sa.String(320)),
        sa.Column("work_phone", sa.String(40)),
        sa.Column("manager_id", sa.Uuid()),
        sa.Column("leave_days_per_year", sa.Numeric(5, 1), server_default="0", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(
            t,
            "type_valid",
            "employment_type IN ('permanent', 'fixed_term', 'casual', 'intern', 'consultant')",
        ),
        _ck(t, "status_valid", "status IN ('active', 'on_leave', 'terminated')"),
        _ck(t, "dates_ordered", "end_date IS NULL OR end_date >= start_date"),
        _fk(t, "user_id", "auth_users.id"),
        _fk(t, "manager_id", "hr_employees.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "employee_no"),
        _uq(t, "user_id"),
    )

    t = "hr_compensation"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("basic_pay", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created(),
        _ck(t, "pay_non_negative", "basic_pay >= 0"),
        _ck(t, "currency_valid", CURRENCY),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "employee_id", "effective_from"),
    )

    t = "hr_contracts"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("file_id", sa.Uuid()),
        sa.Column(
            "signed_copy_on_file", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "dates_ordered", "end_date IS NULL OR end_date >= start_date"),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "file_id", "sys_files.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_employee_id"), t, ["employee_id"])

    t = "hr_leave_requests"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(14), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", sa.Numeric(5, 1), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(10), server_default="pending", nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text()),
        *_ts(),
        _ck(
            t,
            "kind_valid",
            "kind IN ('annual', 'sick', 'maternity', 'paternity', 'compassionate', 'study', 'unpaid')",
        ),
        _ck(t, "status_valid", "status IN ('pending', 'approved', 'rejected', 'cancelled')"),
        _ck(t, "dates_ordered", "end_date >= start_date"),
        _ck(t, "days_positive", "days > 0"),
        _ck(t, "no_self_decision", "decided_by IS NULL OR decided_by <> requested_by"),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "requested_by", "auth_users.id"),
        _fk(t, "decided_by", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_employee_id"), t, ["employee_id"])

    t = "hr_attendance"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        _created(),
        _ck(
            t,
            "status_valid",
            "status IN ('present', 'absent', 'leave', 'remote', 'public_holiday', 'off')",
        ),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "recorded_by", "auth_users.id"),
        _pk(t),
        _uq(t, "employee_id", "work_date"),
    )

    t = "hr_pay_components"
    op.create_table(
        t,
        _id(),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("amount", MONEY, server_default="0", nullable=False),
        sa.Column("rate_pct", sa.Numeric(7, 3), server_default="0", nullable=False),
        sa.Column(
            "bands",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("base", sa.String(8), server_default="gross", nullable=False),
        sa.Column("taxable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source_note", sa.String(300), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "kind_valid", "kind IN ('earning', 'deduction', 'employer')"),
        _ck(t, "method_valid", "method IN ('fixed', 'percent', 'bands')"),
        _ck(t, "base_valid", "base IN ('gross', 'taxable', 'basic')"),
        _ck(t, "values_valid", "amount >= 0 AND rate_pct >= 0 AND rate_pct <= 100"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        _uq(t, "code"),
    )

    t = "hr_payroll_runs"
    op.create_table(
        t,
        _id(),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("total_gross", MONEY, server_default="0", nullable=False),
        sa.Column("total_deductions", MONEY, server_default="0", nullable=False),
        sa.Column("total_net", MONEY, server_default="0", nullable=False),
        sa.Column("total_employer", MONEY, server_default="0", nullable=False),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("prepared_by", sa.Uuid(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        *_ts(),
        _ck(t, "status_valid", "status IN ('draft', 'awaiting_approval', 'approved', 'rejected')"),
        _ck(t, "period_format", PERIOD),
        _ck(t, "currency_valid", CURRENCY),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "prepared_by", "auth_users.id"),
        _pk(t),
    )

    t = "hr_commissions"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("basis", sa.String(300), nullable=False),
        sa.Column("payroll_run_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created(),
        _ck(t, "amount_positive", "amount > 0"),
        _ck(t, "period_format", PERIOD),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "payroll_run_id", "hr_payroll_runs.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
    )

    t = "hr_payslips"
    op.create_table(
        t,
        _id(),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("basic", MONEY, nullable=False),
        sa.Column("gross", MONEY, nullable=False),
        sa.Column("taxable", MONEY, nullable=False),
        sa.Column("deductions", MONEY, nullable=False),
        sa.Column("employer_cost", MONEY, nullable=False),
        sa.Column("net", MONEY, nullable=False),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _fk(t, "run_id", "hr_payroll_runs.id", "CASCADE"),
        _fk(t, "employee_id", "hr_employees.id"),
        _pk(t),
        _uq(t, "run_id", "employee_id"),
    )

    t = "hr_kpis"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("actual", sa.String(200)),
        sa.Column("status", sa.String(10), server_default="agreed", nullable=False),
        sa.Column("employee_agreed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('agreed', 'on_track', 'at_risk', 'met', 'missed')"),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_employee_id"), t, ["employee_id"])

    t = "hr_reviews"
    op.create_table(
        t,
        _id(),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("strengths", sa.Text(), nullable=False),
        sa.Column("improvements", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("employee_comment", sa.Text()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        *_ts(),
        _ck(t, "rating_range", "rating BETWEEN 1 AND 5"),
        _fk(t, "employee_id", "hr_employees.id"),
        _fk(t, "reviewer_id", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_employee_id"), t, ["employee_id"])

    op.execute(FREEZE_SQL)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS hr_compensation_append_only ON hr_compensation; "
        "DROP TRIGGER IF EXISTS hr_payslips_frozen ON hr_payslips; "
        "DROP TRIGGER IF EXISTS hr_payroll_runs_frozen ON hr_payroll_runs; "
        "DROP FUNCTION IF EXISTS hr_append_only(); DROP FUNCTION IF EXISTS hr_guard_approved_run();"
    )
    for table in (
        "hr_reviews",
        "hr_kpis",
        "hr_payslips",
        "hr_commissions",
        "hr_payroll_runs",
        "hr_pay_components",
        "hr_attendance",
        "hr_leave_requests",
        "hr_contracts",
        "hr_compensation",
        "hr_employees",
    ):
        op.drop_table(table)
    op.execute("DROP SEQUENCE hr_employee_ref_seq")
