<!-- Director-supplied Stage 0 specification, complete text re-sent 2026-11-12 (419 lines). Verbatim. -->

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
- One-to-one messaging.
- Department group conversations.
- Director announcements.
- Task assignments.
- Daily reports.
- Acknowledgements.
- Follow-up questions.
- Attachments and document sharing.

Clearly identify AI-generated messages and distinguish them from messages personally sent by the Director.

J. DOCUMENT CENTRE
- PDF generation.
- Excel reports.
- Word documents.
- Quotations.
- Invoices.
- Purchase orders.
- Tender documents.
- Contracts.
- Business correspondence.

K. ADMINISTRATION AND SECURITY
- User management.
- Role-based access.
- Individual permissions.
- Audit logs.
- Security alerts.
- Backup management.
- System configuration.

# 5. STAFF ROLES AND PERMISSIONS

Plan the following roles:
- Director.
- Business Development.
- Procurement.
- Finance.
- Logistics.
- HR/Admin.

All permissions must be enforced on the backend, not merely by hiding buttons in the interface.

Financial records, payroll, confidential supplier information and sensitive company documents must have restricted access.

A user must not approve their own restricted transactions.

# 6. JARVIS SECURITY ARCHITECTURE

Every JARVIS action must follow:

Authentication → Permission verification → Command interpretation → Validation → Approval where required → Execution → Audit logging.

JARVIS must never:
- Execute arbitrary SQL.
- Bypass permissions.
- Make unauthorised payments.
- Change supplier bank information without approval.
- Submit tenders without human approval.
- Impersonate employees.
- Bypass financial controls.
- Perform sensitive actions using voice recognition alone as authentication.

Separate read-only, prepare and execute permissions.

The Director must explicitly authorise sensitive operations.

# 7. DESIGN SYSTEM

Create a premium futuristic AVEN GLOBAL visual identity.

Proposed palette:
- Midnight navy.
- Deep blue.
- Champagne gold.
- Warm white.
- Graphite.

The interface should feature:
- Cinematic login and startup.
- Animated AVEN GLOBAL branding.
- Premium dashboard cards.
- Elegant glass and layered surfaces.
- Subtle holographic accents.
- Smooth transitions.
- Intelligent data visualisations.
- A distinctive JARVIS interface.
- Responsive desktop and mobile layouts.

Avoid cheap-looking neon overload, excessive glowing borders, cluttered dashboards and generic template aesthetics.

Use the Director's reference images as the primary visual design authority once supplied and inspected.

# 8. CLOUD, DATA AND RELIABILITY

Design for a central cloud-hosted database accessible by all authorised devices.

Include:
- Secure authentication.
- Session management.
- Encryption in transit and at rest.
- Automated backups.
- Disaster recovery.
- Backup restoration tests.
- Database migration strategy.
- Application monitoring.
- Error tracking.
- Audit logging.
- Secure secret management.
- Deployment rollback procedures.

Do not invent company transactions, customers, suppliers, staff, tenders, licences or financial records.

Use clearly labelled demonstration data only where necessary.

# 9. REQUIRED STAGE 0 DOCUMENTS

Inspect the existing repository first.

Create or update these files:

1. CLAUDE.md
2. README.md
3. ROADMAP.md
4. PROJECT_STATUS.md
5. CHANGELOG.md
6. docs/architecture/SYSTEM_ARCHITECTURE.md
7. docs/architecture/DATABASE_DESIGN.md
8. docs/architecture/AI_ARCHITECTURE.md
9. docs/architecture/VOICE_AND_SOUND.md
10. docs/architecture/DESIGN_SYSTEM.md
11. docs/security/SECURITY_MODEL.md
12. docs/architecture/DEPLOYMENT_ARCHITECTURE.md
13. docs/architecture/INTEGRATION_STRATEGY.md
14. docs/architecture/REFERENCE_IMAGE_SPECIFICATION.md

The documents must explain the system in enough detail that another developer can understand and implement it without guessing.

Include:
- System architecture diagrams.
- Database entity relationships.
- Module dependencies.
- API strategy.
- Authentication and permission architecture.
- AI execution workflow.
- Voice architecture.
- Audio architecture.
- Design principles.
- Cloud deployment strategy.
- Testing strategy.
- Risks and technical limitations.

# 10. FUTURE DEVELOPMENT STAGES

Create a realistic, dependency-aware roadmap covering:

Stage 0: Architecture and project blueprint.
Stage 1: Repository foundation and development environment.
Stage 2: Authentication and security.
Stage 3: Core design system and interface.
Stage 4: Director dashboard and CRM.
Stage 5: Tender management.
Stage 6: Procurement and suppliers.
Stage 7: Finance and accounting.
Stage 8: Inventory and logistics.
Stage 9: Human resources.
Stage 10: Staff communications.
Stage 11: JARVIS AI integration.
Stage 12: Voice activation and immersive audio.
Stage 13: Documents and external integrations.
Stage 14: Cloud deployment and production readiness.
Stage 15: Mobile experience and native application planning.

You may identify additional necessary stages, but do not skip these requirements.

# 11. STAGE 0 RULES

- Inspect the current repository before changing anything.
- Preserve existing work.
- Do not delete or overwrite approved project files without a clear reason.
- Do not write application features yet.
- Do not deploy.
- Do not introduce production infrastructure.
- Do not expose secrets.
- Do not fabricate business information.
- Document unresolved decisions instead of guessing.
- Identify technical risks and dependencies.
- Create a clear Stage 1 readiness checklist.

# 12. FINAL REPORT

When Stage 0 is complete, report:

1. What you inspected.
2. Every file created.
3. Every file updated.
4. The proposed system architecture.
5. The proposed database design.
6. The security architecture.
7. The JARVIS and voice architecture.
8. The visual design architecture.
9. Any unresolved technical decisions.
10. Any risks or platform limitations.
11. The Stage 1 implementation plan.

Run documentation checks where possible.

Do not claim tests or implementation have passed when they have not been run.

STOP after Stage 0.

Wait for the Director to review and explicitly approve Stage 1 before writing application code.