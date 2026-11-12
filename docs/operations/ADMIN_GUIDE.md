# Administrator guide (Director)

## People and access

- **Invite** staff from Admin → Users. Each person gets one role:
  Business Development, Procurement, Finance, Logistics or HR/Admin.
- Only the Director sees every section. Other roles see their department's
  section only.
- **Individual overrides** grant or deny one permission per person, and need
  a reason. Director-only powers can never be granted.
- **Suspend** a user to end their sessions immediately.
- **Password resets** are one-time links that the Director issues.
- **2FA** is required for the Director, Finance and HR/Admin.

## Approvals

Restricted actions wait in **Approvals**: payments, supplier bank changes,
payroll, purchase orders, tender submissions and credit notes. Nobody can
approve their own request. With only one Director, items the Director raises
need a second approver (see the open decisions).

## JARVIS

- JARVIS is enabled for the Director. You can grant `jarvis.use` to others
  with an override.
- JARVIS reads only what the user may see. It **prepares** tasks and messages,
  and nothing happens until you press **Confirm**.
- It cannot pay, approve, submit tenders or change bank details.
- Usage and cost are recorded per request (`ai_usage`).

## Documents

- Invoices, receipts, purchase orders and delivery notes download as PDF or
  Word with the logo.
- The blank letterhead is on the **Documents** page.
- Every download is recorded with its version and fingerprint. The system
  never applies a signature or stamp.

## Records you cannot change

Posted journals, issued invoices, receipts, stock movements, approved payroll,
messages and the audit log are permanent. Corrections use reversals and credit
notes, which keeps the history honest.

## Staff communications

See `docs/policies/COMMUNICATIONS_POLICY.md`. There is no hidden monitoring.
Give staff that policy before they start using the system.
