# Submission notes

Live URL: pending — no hosting account or public deployment exists yet.
Repository URL: pending — the local Git repository has no remote configured.

The required application is implemented and locally verified. This is not yet a publicly deployed submission. See DEPLOYMENT.md for local startup, container deployment, and GitHub publishing steps.

## Demo access

Run `uv sync --frozen`, then `uv run uvicorn app.main:app --reload`, and open http://localhost:8000. A fresh database contains Wong Li (id 1, supreme), Christine Palmer (id 2, master), Jonathan Pangborn (id 3, adept), and Sara Lin (id 4, apprentice). Select a member in the interface, browse books, create and pay or cancel orders, borrow and return books, and inspect member statistics and sales reports. There is no authentication or real payment processing in this exercise.

## Completed functionality

- Books: ISBN normalization and checksum validation, duplicate protection, creation, retrieval, partial updates, literal text search, filters, pagination, and deterministic sorting.
- Members: normalized email uniqueness, tier access rules, and accurate statistics without multiplying joined rows.
- Orders: validation precedence, price snapshots, tier and bulk discounts, stock reservation, payment, and cancellation with stock restoration.
- Loans: tier limits, restricted access, overdue blocking, duplicate borrowing checks, 14-day due dates, computed status, return fees, and stock restoration.
- Reports: paid-order sales quantities, current book titles, deterministic ranking, and limits.
- Browser interface: repaired the Return button's missing action dispatch; existing catalogue, checkout, cancellation, lending, member, and report workflows work against the implemented API.

## Architecture and data integrity

FastAPI routers handle HTTP and inject the clock. Pydantic schemas normalize and validate inputs. Services implement business rules using synchronous SQLAlchemy sessions. Monetary amounts use integer cents; timestamps use naive UTC values as specified. Loan status is derived from due/return timestamps, and overdue means strictly later than the due time.

Each mutation uses one transaction for domain state and inventory. The shared transaction helper commits once and rolls back exceptions, including failures after SQL flush. It works with SQLAlchemy's existing implicit transaction. Validation completes before changing inventory. Orders snapshot unit prices; loan fee caps use the book price at return and stored fees remain fixed afterward. Member aggregates are calculated separately to avoid join multiplication.

## Testing and verified results

Verified on 27 September 2026 using Python 3.12.12 and the frozen dependency lock:

| Run | Result |
| --- | --- |
| Untouched ZIP starter | 73 passed, 125 failed, 4 setup errors |
| Supplied acceptance suite | 202 passed |
| Additional verification | 45 passed |
| Combined final suite | 247 passed, 2 third-party deprecation warnings |

Command: `uv run --frozen pytest tests verification`.

The supplied tests, pyproject.toml, and uv.lock are unchanged. The additional suite checks 16 injected mutation failures before commit and after flush, independent database snapshots, uniqueness races, unrelated integrity errors, validation boundaries, shared order/loan inventory, microsecond late-fee rounding, aggregate isolation, and real SQLite persistence across application lifespans. Tests required execution outside the desktop sandbox because its restrictions stalled the TestClient event loop; no dependency workaround was added.

Browser verification covered master checkout ($39.99 subtotal, $3.99 discount, $36.00 total), payment, sales reporting, restricted borrowing, return, ISBN-normalized book creation, editing, author search, cancellation restoring stock, and member statistics. Preview data is disposable and is not committed.

The deployment image was built with Podman and run as its non-root user. A second container using the same named volume retained the created member, paid order, active loan, and reduced stock. The container served the UI, API documentation, health endpoint, and repaired frontend Return action. Its Python base provided version 3.12.14; runtime package versions came from the unchanged lockfile.

## Deployment and known limitations

The Dockerfile uses the frozen runtime dependencies, a non-root user, configurable PORT, and SQLite under /data. A durable volume is required. DEPLOYMENT.md explains local containers and the steps needed for public hosting. No provider, hosting account, or GitHub remote has been selected.

Transactions protect each operation's atomicity. Optional protection against simultaneous stock reservations and conflicting state transitions has not been implemented. Optional member-list pagination has not been added. Existing databases with the starter's older loan table need an explicit schema migration or a separately chosen fresh demo database; create_all does not migrate tables and the application never deletes existing data automatically.

The assignment's PostgreSQL suggestion conflicts with its prohibition on new dependencies: the frozen dependencies contain no PostgreSQL driver. Persistent SQLite avoids adding one. Public deployment, logged-out repository access, and public data retention still require verification after accounts are available.

## Git provenance

The downloaded ZIP contained no original Git history or remote URL. All 39 extracted files matched the supplied archive before edits. The ZIP comment includes possible commit identifier 923084c6077223fef006d21409c8a6a917c70a43, which was not independently verified. The untouched snapshot is preserved in local commit 2a07628; subsequent planning, feature implementation, verification, and frontend fixes have incremental commits. This does not recover upstream history or imply the assignment authors approved an exception.

## AI usage

Codex inspected the supplied documents, prepared the implementation plan, implemented the backend, added independent verification, operated the browser for checks, and prepared deployment documentation. The terminal, pytest, Git, browser tools, and container tooling were used to verify results. No supplied acceptance test was changed to make the implementation pass.

A corrected suggestion was the initial emphasis on finding or cloning an upstream repository: the user clarified that the supplied ZIP should be implemented and published to their own GitHub repository. The local import preserves the actual available source without inventing upstream history. Browser inspection also exposed a Return button dispatch omission that backend tests could not detect, and it was repaired and checked through the interface.

The candidate should review and understand the submitted code before discussing it with the reviewers. Further work would prioritize concurrency protection, explicit schema migrations, backups, and public deployment verification.
