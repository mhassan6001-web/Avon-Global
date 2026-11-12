<!-- Director-supplied Stage 0 specification, received 2026-11-12. Verbatim.
     NOTE: the supplied file ends at line 208 ('I. STAFF COMMUNICATIONS -'); the rest was not received. -->

# AVEN GLOBAL | STAGE 0: MASTER ARCHITECTURE AND PROJECT BLUEPRINT

You are working on the AVEN GLOBAL project.

The Director has authorised you to create Stage 0 because the Stage 0 instructions were not previously found.

Do not search endlessly for a missing Stage 0 prompt. The instructions below ARE the official Stage 0 specification.

Your responsibility is to inspect the existing repository, establish the complete technical architecture, create the required documentation and prepare the project for controlled development.

IMPORTANT: Stage 0 is an architecture and planning stage. Do not begin implementing the application yet.

# 1. PRODUCT IDENTITY

Official product name: AVEN GLOBAL.

AVEN GLOBAL is a centralised, cloud-based business operating system for a Malawi-based international procurement, supplies, sourcing, import/export and distribution company.

The system must eventually work across:
- Windows computers.
- macOS computers.
- Smartphones.
- Tablets.
- Supported modern browsers.

The interface must have an exceptionally premium, futuristic, cinematic appearance.

Use a 2050-inspired visual direction, but NEVER include 2050 in the official product name.

# 2. DIRECTOR'S CONFIRMED DESIGN DECISIONS

JARVIS configuration:
- Voice: CINEMATIC.
- Activation: WAKE_WORD.
- Sound: IMMERSIVE.

JARVIS must have an original, deep, polished male-sounding executive voice. It should sound intelligent, articulate, composed, confident and naturally conversational.

Its personality should resemble a professional executive butler, with subtle humour and occasional clever sarcasm.

Do not imitate a copyrighted fictional character, actor or celebrity.

Wake-word activation must be optional, with manual push-to-talk available. Investigate actual browser and mobile operating-system limitations.

Immersive audio should include original or properly licensed:
- Startup sounds.
- JARVIS activation sounds.
- Typing effects.
- Navigation sounds.
- Module-opening effects.
- Notifications.
- Approval and completion sounds.
- Voice-processing feedback.

Include master volume, individual sound controls, mute, quiet mode and reduced-motion settings.

# 3. TECHNICAL ARCHITECTURE

Design a secure, centralised cloud architecture.

Preferred technology direction:

Frontend:
- Next.js.
- TypeScript.
- Responsive web application.
- Installable Progressive Web App.
- Framer Motion for interface animation.

Backend:
- Python.
- FastAPI.
- REST API.
- WebSockets for real-time messaging and notifications.

Database:
- PostgreSQL.
- SQLAlchemy.
- Alembic migrations.
- Proper relational database design.

Background processing:
- Redis.
- Celery or an appropriately justified alternative.

AI:
- Anthropic Claude API integration.
- Provider-independent speech-to-text and text-to-speech architecture.
- Secure AI tool execution layer.

Storage:
- Secure cloud object storage compatible with S3.

Deployment:
- Docker.
- Cloud-hosted production infrastructure.
- HTTPS.
- Secure environment configuration.
- Automated backups and monitoring.

Do not use Supabase or Vercel.

Do not use localhost as the production environment.

Prefer a modular monolith initially. Do not introduce unnecessary microservices.

Document alternatives where technical investigation suggests a better solution. Do not silently change the Director's confirmed requirements.

# 4. COMPANY OPERATING MODULES

Design the system around these modules:

A. DIRECTOR COMMAND CENTRE
- Business overview.
- Revenue and expenses.
- Cash position.
- Profitability.
- Outstanding invoices.
- Supplier liabilities.
- Active tenders.
- Pending approvals.
- Staff performance.
- Alerts and business intelligence.

B. JARVIS AI
- Voice and text interaction.
- Business intelligence.
- Daily executive briefings.
- Report generation.
- Task management.
- Authorised actions.
- Business-wide search.
- Staff communication assistance.

C. CRM AND SALES
- Customer database.
- Prospects.
- Customer contacts.
- Sales pipeline.
- Quotations.
- Contracts.
- Follow-ups.
- Customer history.

D. TENDER MANAGEMENT
- Tender opportunities.
- Government procurement.
- NGO and UN opportunities.
- Tender documents.
- Eligibility requirements.
- Submission deadlines.
- Compliance checklists.
- Bid costing.
- Submission tracking.
- Award and unsuccessful-bid records.

E. PROCUREMENT AND SUPPLIERS
- Supplier database.
- Supplier verification.
- Supplier quotations.
- Purchase requests.
- Purchase orders.
- Approval workflows.
- Procurement tracking.
- Landed-cost calculations.
- Supplier performance.

F. FINANCE AND ACCOUNTING
- Customer invoices.
- Receipts.
- Payments.
- Expenses.
- Cashbook.
- Debtors.
- Creditors.
- Bank reconciliation.
- Profit and loss.
- Balance sheet.
- Cash flow.
- Multi-division profitability.
- Financial reporting.

Use an accountant-reviewable double-entry accounting architecture. Never silently overwrite posted financial transactions. Use appropriate reversal and correction processes.

Support MWK, USD, ZAR and ZMW. Do not hardcode tax rates. Tax configuration and statutory treatment must be reviewed by a qualified Malawi accountant.

G. INVENTORY AND LOGISTICS
- Stock management.
- Warehouses.
- Stock movements.
- Purchase receipts.
- Shipment tracking.
- Customs documentation.
- Delivery management.
- Reorder alerts.
- Stock valuation.

H. HUMAN RESOURCES
- Employee records.
- Employment contracts.
- Attendance.
- Leave.
- Payroll.
- Performance.
- Staff assignments.
- Department management.

I. STAFF COMMUNICATIONS
-

<!-- [END OF RECEIVED TEXT — remainder missing; requested from the Director] -->
