# User acceptance tests

Run these on **staging** with development-only test data, never real records.
Record the result, the tester, the date and the device for each. A test fails
if any step differs from the expected result.

| ID | Role | Steps | Expected |
|----|------|-------|----------|
| UAT-01 | Director | Sign in with 2FA; open the Command Centre | Figures show "No data yet" where nothing is recorded |
| UAT-02 | Director | Invite a Finance user; they accept, set a password and enrol 2FA | They can sign in. Only finance sections are visible. |
| UAT-03 | Business Development | Add a customer, an opportunity and a follow-up | All appear; the follow-up shows in the Command Centre |
| UAT-04 | Business Development | Register a tender and request bid approval | The Director sees it under Approvals; nobody approves their own |
| UAT-05 | Procurement | Verify a supplier, compare two quotations, raise a PO | PO number issued; PDF downloads with the logo and no signature |
| UAT-06 | Procurement | Request a supplier bank change | Bank details stay masked; the change waits for the Director |
| UAT-07 | Finance | Set up accounts, a period and tax codes; issue an invoice | The trial balance is balanced; the invoice PDF and Word match the record |
| UAT-08 | Finance | Record a receipt; issue a credit note | Credit note needs a different approver; posted entries never change |
| UAT-09 | Logistics | Receive goods against a PO; dispatch with a delivery note; record proof | Stock is weighted-average; no negative stock; the delivery note PDF |
| UAT-10 | HR/Admin | Add an employee, record leave, prepare payroll | The Director approves payroll; staff see only their own payslip |
| UAT-11 | Any staff | Messages, tasks, morning plan and end-of-day report | Only members read a conversation; read receipts are shown |
| UAT-12 | Director | JARVIS: "brief me"; ask about approvals; "create task: …" | Briefing from records only; the task waits for **Confirm** |
| UAT-13 | Director | JARVIS asked to pay a supplier or approve a request | Refused; no tool exists for it |
| UAT-14 | Director | Push-to-talk question (once STT is configured) | The microphone closes after sending; no audio is kept |
| UAT-15 | Director | Enable the wake word (once licensed) | Consent screen shown; the decision is recorded; Stop ends capture |
| UAT-16 | Any | Turn sound off and set motion to Off | Every task still works; nothing animates or plays |
| UAT-17 | Any | Install the app on a phone and on a desktop | It opens standalone with the AVEN GLOBAL icon; offline shows a notice and no stale data |
| UAT-18 | Any | Download the letterhead (Word) and type a letter | The logo header repeats on every page |

The voice and wake-word technical criteria (WW-01…08, MP-01…02, VO-01…04,
SC-01…07, SV-01…03, PC-01) are listed in `docs/architecture/VOICE_AND_SOUND.md` §8.
