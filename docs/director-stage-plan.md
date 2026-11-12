<!-- Director's stage plan (Stages 2–15), received 2026-11-12. Verbatim. -->

Implement Stage 2: AVEN GLOBAL Identity and Security.
Build:

* Login and logout
* Secure password hashing
* Password reset
* Session management
* Two-factor authentication
* User administration
* Roles and individual permissions
* Account activation and suspension
* Login history
* Audit logs
* Backend permission enforcement
* Rate limiting
* Secure file access

Create initial roles:
Director, Business Development, Procurement, Finance, Logistics and HR/Admin.
The Director has full authorised access.
Test each role against every protected module.
Prevent unauthorised access to payroll, financial data and supplier bank details.
Use development-only test accounts.
Update security documentation and stop for approval.

Implement Stage 3: AVEN GLOBAL Visual Experience.
Create the production design system and application-wide interaction layer.
Build:

* Animated AVEN GLOBAL startup identity
* Premium navigation transitions
* Holographic-inspired panels
* Glass-style components
* Subtle gold light accents
* Animated charts
* Interactive status indicators
* JARVIS visual placeholder component
* Responsive desktop and mobile layouts
* Framer Motion animation components
* Reduced-motion support

SOUND ENGINE:
Implement an original configurable sound system using suitable licensed or original sound assets.
Include:

* Startup sound
* Typing sound
* Navigation sound
* Module transition sound
* Notification sound
* Approval sound
* Warning sound
* JARVIS activation sound
* Shutdown sound

Provide:

* Master volume
* Individual sound categories
* Mute
* Quiet mode
* Sound previews
* User preferences
* Browser autoplay handling

Never use copyrighted film audio or unauthorised music.
Keep sounds subtle and non-disruptive.
Do not make animations or audio necessary for basic application functionality.
Test performance, accessibility, browser restrictions and mobile behaviour.
Stop for approval.

Implement Stage 4: Director Command Centre and CRM.
DIRECTOR DASHBOARD:

* Invoiced revenue
* Cash collected
* Gross profit
* Expenses
* Cash position
* Outstanding invoices
* Supplier payables
* Tender deadlines
* Pending approvals
* Sales opportunities
* Staff task performance
* Recent company activity

CRM:

* Companies
* Contacts
* Customer categories
* Country and location
* Communication history
* Meetings
* Opportunities
* Sales pipeline
* Follow-ups
* Notes
* Attachments
* Quotations

Use real database records and calculations.
Implement search, filters, permissions and activity history.
Clearly distinguish empty states from actual zero balances.
Test calculations and access controls.
Stop for approval.

Implement Stage 5: AVEN GLOBAL Tender Management.
Build a full tender register for RFQs, RFPs, EOIs and procurement opportunities.
Include:

* Issuing organisation
* Reference number
* Country
* Procurement category
* Publication date
* Closing deadline
* Eligibility
* Required documents
* Specifications
* Bid security
* Assigned officer
* Internal review
* Supporting files
* Submission checklist
* Submission evidence
* Tender result
* Award tracking

Build deadline alerts, bid readiness checks and a Director overview.
External monitoring must use permitted sources and record source links and last-checked dates.
Do not invent opportunities or submit bids automatically.
Test deadline logic, document requirements and permissions.
Stop for approval.

Implement Stage 6: AVEN GLOBAL Procurement.
Build:

* Supplier register
* Supplier verification
* Supplier categories
* Manufacturer/distributor status
* Certificate storage
* Supplier contacts
* Supplier quotation records
* Product specifications
* Purchase requests
* Price comparisons
* Currency conversion records
* Freight
* Insurance
* Duties and taxes
* Local delivery
* Landed-cost calculations
* Purchase approvals
* Purchase orders
* Delivery tracking

Protect supplier bank details.
Require controlled approval for supplier bank changes.
Prevent users from approving restricted requests they created.
Test calculations, permissions and purchase workflows.
Do not invent suppliers or certificates.
Stop for approval.

Implement Stage 7: AVEN GLOBAL Finance and Accounting.
Build an accountant-reviewable financial system with:

* Chart of accounts
* Double-entry accounting
* General ledger
* Customer invoices
* Supplier bills
* Receipts
* Payments
* Expenses
* Cashbook
* Bank reconciliation
* Debtors and creditors
* Credit notes
* Financial periods
* Multi-currency
* Exchange-rate records
* Tax configuration
* Profit and loss
* Balance sheet
* Cash flow
* Contract profitability
* Division profitability

Generate branded PDFs for invoices, receipts and statements.
Support MWK, USD, ZAR and ZMW.
Never hardcode tax rates.
Never silently overwrite posted transactions.
Use reversals and credit notes for corrections.
Test balanced journal entries, duplicate prevention, invoice-to-receipt reconciliation and reports.
Require accountant review of statutory configuration before live use.
Stop for approval.

Implement Stage 8: AVEN GLOBAL Inventory and Logistics.
Build:

* Product catalogue
* SKUs and barcodes
* Categories and units
* Warehouses
* Stock movements
* Goods received
* Stock adjustments
* Stock reservations
* Dispatches
* Returns
* Stock valuation
* Reorder alerts
* Shipment tracking
* Freight details
* Customs documents
* Delivery schedules
* Delivery notes
* Proof of delivery

Support direct-to-customer fulfilment without unnecessary warehouse stock.
Use auditable stock movements.
Test stock balances, valuation and movement history.
Stop for approval.

Implement Stage 9: AVEN GLOBAL Staff and HR.
Build:

* Employee profiles
* Departments
* Employment contracts
* Salary records
* Attendance
* Leave requests
* Leave balances
* Payroll preparation
* Commission schedules
* Performance targets
* KPI tracking
* Reviews
* Training records

Restrict salary and personal information.
Make payroll and statutory calculations configurable and subject to local professional review.
Build individual employee dashboards.
Test employee permissions and payroll calculations.
Stop for approval.

Implement Stage 10: AVEN GLOBAL Staff Communications.
Build a live internal communications system.
FEATURES:

* One-to-one messaging
* Department channels
* Company announcements
* File attachments
* Read acknowledgements
* Task assignments
* Task priorities
* Deadlines
* Task status
* Employee work plans
* End-of-day reports
* Director follow-up questions
* Overdue task alerts
* Searchable conversation history

The Director must be able to ask an employee about their daily activities and continue the discussion.
JARVIS will later use the same authorised messaging services.
Ensure messages identify their sender and distinguish AI-generated messages from messages personally sent by the Director.
Do not implement hidden surveillance.
Test live updates, notifications, permissions and task workflows.
Stop for approval.

Implement Stage 11: AVEN GLOBAL JARVIS AI Core.
Integrate Claude through a secure server-side provider abstraction.
Build:

* Conversation management
* Business knowledge retrieval
* Permission-filtered records
* Structured tool calling
* AI tool execution logs
* Usage and cost tracking
* Error handling
* Daily briefings
* Business analysis
* Task preparation
* Staff communication
* Report generation

Initial tools:

* Get director briefing
* Get revenue summary
* Get cash position
* Find overdue invoices
* Find supplier payables
* Search tenders
* Compare supplier quotations
* Search customers
* Create tasks
* Assign tasks
* Send staff messages
* Request staff reports
* Draft invoices
* Draft quotations
* Draft purchase orders
* Generate reports
* Search authorised documents

Only implement tools when their underlying modules exist.
JARVIS must use backend business services and never arbitrary SQL.
Enforce read, prepare and execute permissions.
Require human approval for sensitive actions.
Test every tool and permission boundary.
Stop for approval.
Implement Stage 12: AVEN GLOBAL JARVIS Voice System.
Build a natural conversational voice interface.
Features:

* Push-to-talk
* Microphone permissions
* Speech-to-text
* Claude reasoning
* Tool calling
* Text-to-speech
* Streaming where supported
* Interruptible speech
* Conversation history
* Voice settings
* Voice/text switching
* Error recovery

Create an original deep, refined, intelligent male-sounding assistant voice.
Do not imitate an existing film character or actor.
Implement:

* JARVIS activation animation
* Animated sound waveform
* Listening indicator
* Processing indicator
* Speaking indicator
* Muted state
* Stop speaking button
* Voice volume
* Speech speed

Optional wake-word support only where technically feasible and privacy-safe.
Sensitive actions must require authenticated confirmation.
Test transcription errors, ambiguous commands, interruptions, permissions and failed API calls.
Stop for approval.

Implement Stage 13: AVEN GLOBAL Documents and Integrations.
Build professional document generation:

* Quotations
* Invoices
* Receipts
* Statements
* Purchase orders
* Delivery notes
* Contracts
* Tender packs
* Reports

Support PDF, Word and Excel.
Build secure integration interfaces for:

* Email
* Calendar
* File storage
* AI
* Voice services
* Notifications

Implement reminders for:

* Tender deadlines
* Invoice due dates
* Supplier deliveries
* Staff tasks
* Meetings
* Approvals

Do not assume external accounts are connected.
Do not send or submit documents without required authorisation.
Test document accuracy and integration failures.
Stop for approval.

Implement Stage 14: AVEN GLOBAL Production Readiness.
Conduct full system testing.
Verify:

* Login and permissions
* Database integrity
* Accounting
* Invoicing
* Procurement
* Tender management
* Staff communications
* JARVIS AI
* Voice execution
* Document generation
* Mobile responsiveness
* Sound settings
* Animation performance
* Backup and recovery
* Security
* Monitoring

Prepare:

* Cloud deployment
* HTTPS
* Production PostgreSQL
* Secure environment secrets
* Persistent file storage
* Automated backups
* Restore tests
* Monitoring
* Error reporting
* Migration process
* Rollback plan

Create:

* PRODUCTION_CHECKLIST.md
* USER_ACCEPTANCE_TESTS.md
* DISASTER_RECOVERY.md
* DEPLOYMENT_GUIDE.md
* ADMIN_GUIDE.md

Do not claim production readiness unless critical tests pass.
Do not deploy without explicit Director approval.
Stop and present a full launch report.

Implement Stage 15: AVEN GLOBAL Mobile Experience.
First create a polished installable Progressive Web App.
Requirements:

* iPhone and Android layouts
* App icon
* Splash screen
* Secure login
* Director dashboard
* JARVIS voice
* Invoices and finance tracking
* Tender alerts
* Staff messages
* Task management
* Document viewing
* Notifications
* Responsive navigation

The mobile application must use the same central backend and business rules.
After PWA verification, assess native iOS and Android development.
Do not duplicate accounting or business logic on mobile.
Do not publish to app stores without explicit Director approval.
Stop and provide the mobile release report.


for jarvis

JARVIS's permanent personality
Ask Claude to create `backend/app/ai/prompts/jarvis_personality.md`.
Use this as its starting personality: