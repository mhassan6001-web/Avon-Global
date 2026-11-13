# Hosting: free and low-cost ways to start (2026-11-12)

The Director asked whether hosting can be free for now. Short answer: **yes for
testing, not for running the real business.** Nothing here has been signed up
for.

| Option | Cost | Good for | Limits |
|--------|------|----------|--------|
| **A. Your own computer** (Docker Desktop, `make up`) | Free | Trying every screen yourself today, with test data | Only works on that computer while it is on. Not reachable by staff or phones. No backups. **Never for real records** (master rule: localhost is never production). |
| **B. Azure free account** | USD 200 credit for the first 30 days, then some services free for 12 months, including 750 hours a month of a small PostgreSQL server (B1ms) with 32 GB storage, and a small Linux virtual machine | A private online test system that you and staff can reach, in the same cloud we plan to use | New Azure customers only. You must switch to pay-as-you-go within 30 days to keep the 12-month free services, and anything beyond the free amounts is charged. ⚠ Whether the free amounts apply in South Africa North must be checked at sign-up. [Microsoft](https://azure.microsoft.com/free/postgresql/) |
| **C. Oracle Cloud "Always Free"** | Free with no end date: a small Arm server | A long-running free test server | Reduced in June 2026 to 2 processors and 12 GB of memory on free accounts; capacity is not guaranteed; no managed database on the same terms. A different cloud from the one planned. [InfoQ](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) |

## Recommendation

1. **Now:** option A on your computer, so you can click through the system
   with test data. I can set it up with you.
2. **When staff need to try it:** option B. It is the same platform as the
   planned production, so nothing is thrown away.
3. **Before real records go in:** the paid production setup, with backups,
   restore tests and monitoring (`docs/operations/PRODUCTION_CHECKLIST.md`).
   The free tiers do not give you tested backups or a standby database.

Opening any cloud account needs a payment card for identity checks, so it
stays your decision.
