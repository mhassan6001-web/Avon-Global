# AVEN GLOBAL database design

- Status: **Stage 0 deliverable, awaiting Director review.** This is the
  logical design. Each stage turns its part into Alembic migrations, and
  details may be refined in that stage's approved plan.
- Implemented today: migration `0001`, `organisation_profile` (Stage 1,
  verified in CI).

## 1. Principles

1. **PostgreSQL 16 is the single system of record.** There is no second
   database. Redis holds only disposable data: cache, rate limits, pub/sub and
   the broker.
2. **Integrity lives in the database:**
   - foreign keys
   - `NOT NULL`
   - CHECK constraints on statuses, currencies and signs
   - unique constraints on document numbers
   - triggers for append-only tables and balanced journals
3. **Never invent business data.** Migrations seed only reference data:
   roles, permissions, currencies, chart-of-accounts *templates* marked for
   accountant review, and units of measure.
4. **Posted financial records are immutable.** Corrections are reversals and
   credit notes. Master data is archived (`archived_at`), not deleted.
5. **Migrations** are linear, reviewed, and reversible where data allows.
   Large changes use expand → migrate → contract. Destructive steps need
   Director approval and a verified backup.

## 2. Conventions

| Item | Convention |
|------|-----------|
| Primary keys | `id UUID DEFAULT gen_random_uuid()` |
| Table names | snake_case, module prefix: `auth_`, `org_`, `crm_`, `tnd_`, `prc_`, `fin_`, `inv_`, `log_`, `hr_`, `com_`, `doc_`, `ai_`, `sys_` |
| Audit columns | `created_at`, `updated_at` (`timestamptz`, UTC), `created_by` and `updated_by` (FK `auth_users`), `version int` (optimistic locking) |
| Money | `NUMERIC(20,4)` plus `currency CHAR(3)` (CHECK in `org_currencies`). Never floating point. |
| Functional currency | MWK. Every financial line stores `amount`, `currency`, `fx_rate_id` and `amount_functional` (MWK). |
| Quantities | `NUMERIC(18,4)` with a `uom_id` |
| Enumerations | `VARCHAR` plus a CHECK constraint (not PG enums, which are easier to evolve) |
| Constraint names | Fixed naming convention (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`), in place since Stage 1 |
| Soft delete | Only for master data (`archived_at`). Transactions are never soft-deleted. |
| Text search | `tsvector` generated columns plus GIN indexes on searchable entities |
| Division and contract tagging | `division_id` on revenue and cost records. `contract_id` or `project_ref` on finance lines for profitability. |

## 3. Platform and security (Stages 1–2)

```mermaid
erDiagram
  auth_users ||--o{ auth_sessions : has
  auth_users ||--o| auth_user_mfa : enrols
  auth_users ||--o{ auth_user_roles : assigned
  auth_roles ||--o{ auth_user_roles : grants
  auth_roles ||--o{ auth_role_permissions : includes
  auth_permissions ||--o{ auth_role_permissions : in
  auth_users ||--o{ auth_permission_overrides : has
  auth_permissions ||--o{ auth_permission_overrides : for
  auth_users ||--o{ auth_invitations : invited
  auth_users ||--o{ auth_reset_tokens : resets
  auth_users ||--o{ auth_login_events : logs
  auth_users ||--o{ sys_audit_events : acts
  org_departments ||--o{ auth_users : employs
  auth_users ||--o{ sys_files : uploads
  sys_approval_requests }o--|| auth_users : requested_by
  sys_approval_requests }o--o| auth_users : decided_by

  auth_users {
    uuid id PK
    citext email UK
    text display_name
    uuid department_id FK
    varchar status "invited|active|suspended"
    text password_hash "argon2id"
    timestamptz password_changed_at
    boolean is_dev_account
  }
  auth_sessions {
    uuid id PK
    uuid user_id FK
    bytea token_sha256 UK
    bytea csrf_token_sha256
    timestamptz last_seen_at
    timestamptz expires_at
    timestamptz step_up_at
    inet ip
    text user_agent
    timestamptz revoked_at
  }
  auth_user_mfa {
    uuid user_id PK
    bytea totp_secret_encrypted
    jsonb recovery_code_hashes
    timestamptz enrolled_at
  }
  auth_roles {
    uuid id PK
    varchar code UK "director|business_development|procurement|finance|logistics|hr_admin"
    text name
  }
  auth_permissions {
    uuid id PK
    varchar code UK "module.resource.action"
    boolean sensitive
  }
  auth_permission_overrides {
    uuid id PK
    uuid user_id FK
    uuid permission_id FK
    varchar effect "grant|deny"
    uuid granted_by FK
    text reason
  }
  auth_login_events {
    uuid id PK
    uuid user_id FK "nullable for unknown accounts"
    varchar outcome "success|bad_password|locked|mfa_failed|suspended"
    inet ip
    timestamptz occurred_at
  }
  sys_audit_events {
    bigint seq PK
    uuid actor_id FK
    varchar actor_kind "user|jarvis_on_behalf|system"
    varchar action
    varchar target_type
    uuid target_id
    jsonb before_redacted
    jsonb after_redacted
    varchar request_id
    bytea prev_hash
    bytea hash "sha256(prev_hash || row)"
    timestamptz occurred_at
  }
  sys_files {
    uuid id PK
    varchar module
    varchar required_permission
    text storage_key
    varchar mime_type
    bigint size_bytes
    bytea sha256
    uuid owner_id FK
  }
  sys_approval_requests {
    uuid id PK
    varchar subject_type
    uuid subject_id
    varchar permission_required
    uuid requested_by FK
    uuid decided_by FK
    varchar status "pending|approved|rejected|cancelled"
    timestamptz decided_at
  }
```

**Other platform tables:**

- `org_organisation_profile`. This is the Stage 1 `organisation_profile`; it
  will be renamed with an expand/contract migration.
- `org_divisions`: the six proposed divisions are **configuration entered by
  the Director**, not seeded.
- `org_departments`
- `org_currencies`
- `org_fx_rates` (`base`, `quote`, `rate`, `rate_date`, `source`,
  `source_url`, `captured_at`; unique per currency pair, date and source)
- `sys_settings` (system configuration, Director-only)
- `sys_outbox` (domain events)
- `sys_security_alerts`
- `sys_backup_runs` (backup management visibility)
- `sys_number_sequences` (`doc_type`, `year`, `next_value`). Numbers are
  allocated with `SELECT … FOR UPDATE` inside the business transaction, so
  they are gapless and unique.

**Database-level protections:**

- `sys_audit_events` has a `BEFORE UPDATE OR DELETE` trigger that raises an
  error, and the application role has only `INSERT, SELECT` on it.
- A nightly job verifies the hash chain and raises a security alert if it is
  broken.

## 4. CRM, quotations and contracts (Stage 4)

```mermaid
erDiagram
  crm_companies ||--o{ crm_contacts : employs
  crm_companies ||--o{ crm_opportunities : has
  crm_companies ||--o{ crm_activities : history
  crm_opportunities ||--o{ crm_quotations : quoted
  crm_quotations ||--o{ crm_quotation_lines : contains
  crm_quotations ||--o| crm_contracts : becomes
  crm_companies ||--o{ crm_followups : scheduled
  crm_companies {
    uuid id PK
    text name
    varchar kind "customer|prospect"
    varchar category
    char country_code
    text city
    tsvector search
  }
  crm_opportunities {
    uuid id PK
    uuid company_id FK
    varchar stage "lead|qualified|proposal|negotiation|won|lost"
    numeric value_estimate
    char currency
    uuid division_id FK
    uuid owner_id FK
  }
  crm_quotations {
    uuid id PK
    varchar number UK
    uuid company_id FK
    varchar status "draft|sent|accepted|rejected|expired"
    char currency
    date valid_until
    int revision
  }
  crm_quotation_lines {
    uuid id PK
    uuid quotation_id FK
    text description
    numeric quantity
    numeric unit_price
    uuid tax_code_id FK
  }
  crm_contracts {
    uuid id PK
    varchar number UK
    uuid company_id FK
    date start_date
    date end_date
    numeric contract_value
    char currency
  }
```

**Other CRM tables:**

- `crm_activities`: meetings, calls, notes and emails logged, plus
  attachments through `sys_files`.
- `crm_followups`: due date, assignee, done.

## 5. Tenders (Stage 5)

```mermaid
erDiagram
  tnd_tenders ||--o{ tnd_requirements : requires
  tnd_tenders ||--o{ tnd_documents : has
  tnd_tenders ||--o{ tnd_checklist_items : checklist
  tnd_tenders ||--o| tnd_bid_costing : costed
  tnd_bid_costing ||--o{ tnd_bid_cost_lines : lines
  tnd_tenders ||--o{ tnd_reviews : reviewed
  tnd_tenders ||--o| tnd_submission : submitted
  tnd_tenders ||--o| tnd_outcome : result
  tnd_sources ||--o{ tnd_tenders : found_via
  tnd_tenders {
    uuid id PK
    varchar kind "rfq|rfp|eoi|itb|other"
    text issuing_org
    varchar issuer_type "government|ngo|un|private"
    varchar reference_no
    char country_code
    varchar category
    date published_on
    timestamptz closing_at "with issuer timezone"
    varchar status "identified|assessing|preparing|internal_review|submitted|won|lost|withdrawn"
    uuid assigned_officer_id FK
    numeric bid_security_amount
    char bid_security_currency
    text source_url
    timestamptz source_last_checked_at
  }
  tnd_sources {
    uuid id PK
    text name
    text base_url
    varchar access_method "rss|api|manual"
    text terms_note
  }
  tnd_submission {
    uuid tender_id PK
    timestamptz submitted_at
    uuid submitted_by FK
    uuid approved_by FK
    uuid evidence_file_id FK
  }
  tnd_outcome {
    uuid tender_id PK
    varchar result "awarded|unsuccessful|cancelled"
    numeric award_value
    text notes
  }
```

Rules:

- A submission requires an approval request decided by the Director. It is
  never automatic.
- Readiness means every mandatory checklist item is done.

## 6. Procurement and suppliers (Stage 6)

```mermaid
erDiagram
  prc_suppliers ||--o{ prc_supplier_contacts : has
  prc_suppliers ||--o{ prc_supplier_certificates : holds
  prc_suppliers ||--o{ prc_supplier_bank_accounts : paid_to
  prc_supplier_bank_accounts ||--o{ prc_bank_change_requests : changed_by
  prc_purchase_requests ||--o{ prc_pr_lines : contains
  prc_purchase_requests ||--o{ prc_supplier_quotes : solicits
  prc_supplier_quotes ||--o{ prc_quote_lines : prices
  prc_supplier_quotes ||--o{ prc_landed_costs : costed
  prc_purchase_orders ||--o{ prc_po_lines : contains
  prc_suppliers ||--o{ prc_purchase_orders : receives
  prc_purchase_orders ||--o{ prc_delivery_tracking : tracked
  prc_suppliers ||--o{ prc_performance_reviews : rated
  prc_suppliers {
    uuid id PK
    text legal_name
    varchar category
    varchar supplier_type "manufacturer|distributor|agent|service"
    char country_code
    varchar verification_status "unverified|in_review|verified|rejected"
  }
  prc_supplier_bank_accounts {
    uuid id PK
    uuid supplier_id FK
    bytea account_details_encrypted "column-encrypted"
    varchar masked_display
    boolean active
    uuid approved_by FK
  }
  prc_bank_change_requests {
    uuid id PK
    uuid bank_account_id FK
    bytea proposed_details_encrypted
    uuid requested_by FK
    uuid approval_request_id FK
    varchar status
  }
  prc_landed_costs {
    uuid id PK
    uuid supplier_quote_id FK
    numeric goods_value
    numeric freight
    numeric insurance
    numeric duties
    numeric taxes
    numeric local_delivery
    uuid fx_rate_id FK
    numeric total_functional
  }
  prc_purchase_orders {
    uuid id PK
    varchar number UK
    uuid supplier_id FK
    varchar status "draft|pending_approval|approved|sent|partially_received|received|closed|cancelled"
    char currency
    uuid approval_request_id FK
  }
```

Bank details are **encrypted at column level** (an application key held in
secrets). They can be read only with `procurement.supplier_bank.view` (Director
by default). Changes take effect only after the approval request is decided by
a **different** user, with step-up authentication.

## 7. Finance and accounting (Stage 7)

```mermaid
erDiagram
  fin_accounts ||--o{ fin_journal_lines : posted_to
  fin_journal_entries ||--|{ fin_journal_lines : balances
  fin_periods ||--o{ fin_journal_entries : within
  fin_journal_entries ||--o| fin_journal_entries : reverses
  fin_invoices ||--|{ fin_invoice_lines : contains
  fin_invoices ||--o| fin_journal_entries : posts
  fin_receipts ||--o{ fin_receipt_allocations : allocates
  fin_invoices ||--o{ fin_receipt_allocations : settled_by
  fin_credit_notes }o--|| fin_invoices : corrects
  fin_bills ||--|{ fin_bill_lines : contains
  fin_payments ||--o{ fin_payment_allocations : allocates
  fin_bills ||--o{ fin_payment_allocations : settled_by
  fin_bank_accounts ||--o{ fin_bank_statement_lines : imports
  fin_bank_statement_lines ||--o| fin_reconciliation_matches : matched
  fin_tax_codes ||--o{ fin_tax_rates : rates
  fin_accounts {
    uuid id PK
    varchar code UK
    text name
    varchar type "asset|liability|equity|income|expense"
    boolean is_control
    boolean template_needs_accountant_review
  }
  fin_journal_entries {
    uuid id PK
    varchar number UK
    date entry_date
    uuid period_id FK
    varchar source_type
    uuid source_id
    varchar status "draft|posted"
    uuid reverses_entry_id FK
    uuid posted_by FK
    timestamptz posted_at
  }
  fin_journal_lines {
    uuid id PK
    uuid entry_id FK
    uuid account_id FK
    numeric debit "functional MWK"
    numeric credit "functional MWK"
    numeric amount_txn
    char currency_txn
    uuid fx_rate_id FK
    uuid division_id FK
    uuid contract_id FK
  }
  fin_periods {
    uuid id PK
    date starts_on
    date ends_on
    varchar status "open|closed|locked"
  }
  fin_invoices {
    uuid id PK
    varchar number UK
    uuid customer_id FK
    varchar status "draft|posted|partially_paid|paid|credited"
    char currency
    date due_date
  }
  fin_tax_rates {
    uuid id PK
    uuid tax_code_id FK
    numeric rate
    date effective_from
    uuid approved_by_accountant FK
  }
```

**Invariants (database and service enforced, property-tested):**

- Σ debit = Σ credit per entry: a deferred constraint trigger fires at
  commit.
- No line has both a debit and a credit, and no line is negative.
- A posted entry and its lines are read-only (trigger). Corrections are a new
  entry with `reverses_entry_id`.
- Posting into a `closed` or `locked` period is rejected.
- Invoice, receipt, credit-note, bill and payment numbers are unique and
  gapless per type and year.
- **Invoiced revenue** (posted invoices) and **cash collected** (receipts)
  are separate ledgers and separate reports.
- No tax rate exists in code. Rates come from `fin_tax_rates`, each with
  accountant approval recorded.

## 8. Inventory and logistics (Stage 8)

```mermaid
erDiagram
  inv_products ||--o{ inv_skus : variants
  inv_skus ||--o{ inv_stock_movements : moves
  inv_warehouses ||--o{ inv_stock_movements : at
  inv_stock_movements }o--o| prc_purchase_orders : received_from
  inv_skus ||--o{ inv_reservations : reserved
  log_shipments ||--o{ log_shipment_items : carries
  log_shipments ||--o{ log_customs_documents : cleared_with
  log_shipments ||--o{ log_tracking_events : tracked
  log_deliveries ||--o| log_proof_of_delivery : confirmed
  inv_skus {
    uuid id PK
    varchar sku UK
    varchar barcode
    uuid uom_id FK
    numeric reorder_level
  }
  inv_stock_movements {
    uuid id PK
    uuid sku_id FK
    uuid warehouse_id FK "null for direct-to-customer"
    varchar kind "receipt|dispatch|adjustment|transfer|return"
    numeric quantity "signed"
    numeric unit_cost_functional
    varchar reference_type
    uuid reference_id
  }
  log_shipments {
    uuid id PK
    varchar reference UK
    varchar mode "sea|air|road|courier"
    varchar incoterm
    text carrier
    varchar status
  }
```

- Stock balances are derived from movements, which are append-only, plus a
  cached balance table rebuilt by a job and checked against the movements.
- Valuation uses weighted average (proposed; to be confirmed with the
  accountant).
- Direct-to-customer fulfilment uses movements with no warehouse.

## 9. Human resources (Stage 9)

```mermaid
erDiagram
  hr_employees ||--o{ hr_contracts : employed_under
  hr_employees ||--o{ hr_salary_records : paid
  hr_employees ||--o{ hr_leave_requests : requests
  hr_employees ||--o{ hr_attendance : records
  hr_employees ||--o{ hr_reviews : reviewed
  hr_payroll_runs ||--|{ hr_payslips : produces
  hr_employees ||--o{ hr_payslips : receives
  org_departments ||--o{ hr_employees : contains
  hr_employees {
    uuid id PK
    uuid user_id FK "nullable"
    uuid department_id FK
    text full_name
    date start_date
    varchar status
  }
  hr_salary_records {
    uuid id PK
    uuid employee_id FK
    numeric gross_amount "restricted"
    char currency
    date effective_from
  }
  hr_payroll_runs {
    uuid id PK
    date period_start
    date period_end
    varchar status "draft|prepared|approved|posted"
    uuid prepared_by FK
    uuid approved_by FK
  }
```

- Salary, payslip and personal-identifier columns are visible only with
  `hr.payroll.view` (Director and HR/Admin).
- Statutory deduction rules are configuration (`hr_statutory_rules`), and
  require professional sign-off.

## 10. Communications (Stage 10)

```mermaid
erDiagram
  com_channels ||--o{ com_channel_members : includes
  com_channels ||--o{ com_messages : contains
  com_messages ||--o{ com_message_receipts : read_by
  com_messages ||--o{ com_attachments : attaches
  com_tasks ||--o{ com_task_updates : progresses
  com_tasks ||--o{ com_reports : reported_in
  com_messages {
    uuid id PK
    uuid channel_id FK
    uuid sender_user_id FK
    varchar sender_kind "person|jarvis_on_behalf"
    uuid on_behalf_of_user_id FK
    text body
    boolean requires_ack
    tsvector search
  }
  com_tasks {
    uuid id PK
    text title
    uuid assignee_id FK
    uuid assigned_by FK
    varchar priority "low|normal|high|urgent"
    timestamptz due_at
    varchar status "open|in_progress|blocked|done|cancelled"
  }
```

`sender_kind` and `on_behalf_of_user_id` make AI-generated messages
**structurally distinguishable** from messages the Director sent personally.

## 11. Documents and AI (Stages 11–13)

- **`doc_documents`:** `type`, `number`, `source_type` and `source_id`,
  `version`, `file_id`, `generated_by`, `status`. The table is versioned and
  never overwritten. There are no signature images unless uploaded and
  authorised.
- **AI tables:**
  - `ai_conversations` and `ai_messages`
  - `ai_tool_calls` (tool, category read/prepare/execute, inputs redacted,
    decision, outcome, `approval_request_id`, `audit_seq`)
  - `ai_usage` (tokens, cost, latency, user)
  - `ai_voice_consents` (user, device, consented_at, revoked_at)

## 12. Retention (proposed, Director to confirm)

| Data | Retention |
|------|-----------|
| Audit, login events | 7 years |
| Financial records | At least 7 years, or as the accountant advises |
| Messages | Per the communications policy (Stage 10 decision) |
| Voice audio | **Not stored** (deleted after transcription). Transcripts follow the messages policy. |
| Sessions, reset tokens | Removed after expiry plus 30 days |
