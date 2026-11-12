# Disaster recovery runbook

Targets: **RPO ≤ 15 minutes, RTO ≤ 4 hours** (`DEPLOYMENT_ARCHITECTURE.md` §6).
Every restore that replaces production needs Director approval.

## 1. Declare and contain

1. Record the time, the symptoms and who is involved.
2. If data is being damaged, put the app into maintenance by scaling the web
   and API services to zero. Do not delete anything.
3. Inform the Director.

## 2. Choose the recovery path

| Situation | Path |
|-----------|------|
| Bad release, data fine | Redeploy the previous image tag (expand-only migrations make this safe) |
| Bad migration | Run the tested down-migration or a forward fix; never edit posted records by hand |
| Data corruption or deletion | Point-in-time restore **into a new instance** (step 3) |
| Region outage | Restore the latest cross-region snapshot in the second region |

## 3. Point-in-time restore

1. Restore the database to a new instance at a timestamp just before the
   incident.
2. Point a staging API at it and run the integrity checks:
   - `alembic current` equals the expected head
   - the trial balance is balanced for every open period
   - journal, receipt, invoice and credit-note number sequences have no gaps
   - append-only tables (journals, stock movements, messages, audit) have
     row counts no lower than at the last backup check
3. The Director approves the switch-over. Then repoint production secrets and
   scale up.
4. Keep the damaged instance read-only for investigation.

## 4. After recovery

- Write an incident report: timeline, cause, data lost (if any), fixes.
- Run a restore test of the new backups within 7 days.

## 5. Rehearsal

Rehearse the full restore at least every quarter. Record the result and the
time taken.
