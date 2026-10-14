# Trade-offs and Performance Considerations

## Design trade-offs

| Choice | Benefit | Cost or limitation |
|---|---|---|
| SQLite local file | Simple setup, portable development/demo, fast for the current single-process dataset | Limited write concurrency and operational scaling; the database URL is currently fixed in code, so deployment to a managed DB requires code/configuration work |
| Stateless signed bearer tokens | Simple API authentication without server-side session storage | Tokens remain valid until expiry; no token revocation/refresh flow is currently implemented. Protect transport and storage, and keep expiry and key rotation operationally managed |
| PBKDF2 password hashing | Uses a salted, standard-library password KDF without an additional runtime service | Iteration count is fixed in code and should be periodically reviewed against deployment hardware and current security guidance |
| One current profile row plus dated salary rows | Makes employee browsing simple while preserving compensation history | Cross-record date rules are enforced in route logic; concurrent writers need transactional conflict handling and database-level protections if deployed at scale |
| Currency-specific salary statistics | Avoids presenting invalid comparisons between unlike currencies | Does not provide an organization-wide converted total; conversion would require a trusted rate source, rate dates, and explicit reporting policy |
| In-memory median calculation | Straightforward and exact for the current size, with no database-specific percentile support needed | Reads salary amounts into the application process and becomes more memory/CPU intensive as the dataset grows |
| CSV staging before writes | Avoids partial import when file validation fails and produces row-level errors | Retains parsed rows and some lookup data in memory; impose size/row limits and consider streaming or background jobs for substantially larger imports |
| LocalStorage bearer-token storage | Simple integration for this single-page application | JavaScript-accessible storage is exposed to successful XSS; a production threat model may prefer secure, HttpOnly, SameSite cookies and corresponding CSRF controls |

## Performance test notes

Measurements below are a local point-in-time smoke check on the seeded SQLite database, not a benchmark or service-level objective:

| Operation | Observed data | Observed elapsed time |
|---|---:|---:|
| `GET /employees?page=1&size=200` | 200 returned rows; 10,003 total employees during the measurement | ~37 ms |
| `GET /analytics/summary` | 10,003 employees | ~90 ms |
| `GET /employees/export-csv?search=WEBHARD-2026-01` | One matching employee; valid `text/csv` response | ~Not separately timed |

The two browser-test employees used during measurement were subsequently deleted; the local seeded dataset returned to 10,001 employees. Timings can vary with machine load, database cache, and process state.

## Implemented query controls

- Employee list pagination validates `page >= 1` and constrains page size to `1..200`.
- Current salary for list/export rows is selected with a correlated latest-record query, rather than issuing a separate salary query for each employee.
- The hardening test observes SQL statements for an authenticated five-employee list request and asserts the read-query count stays at or below three; this guards against an N+1 regression rather than measuring latency.
- CSV export applies the supported employee filters in the database query.
- SQLite indices exist on commonly filtered and joined employee fields and salary/audit foreign keys.

## Likely bottlenecks and future work

1. **Analytics scans:** Analytics currently loads employee dimensions into Python to group country, department, job title, and status. SQL `GROUP BY` can reduce transfer and application memory if the dataset grows considerably.
2. **Median computation:** The salary route loads current salary values per currency into memory. Consider database-specific percentile functions or an analytics/warehouse layer only when volume warrants the added complexity.
3. **Search indexes:** Employee search uses case-insensitive substring matching over several text columns. A leading wildcard typically prevents ordinary B-tree indexes from helping; evaluate full-text search or a dedicated search index if search latency becomes material.
4. **CSV scale:** Uploads are capped at 5 MiB, but current CSV parsing and staged updates are synchronous. For much larger imports, add row-count limits, background processing, job status, and a downloadable validation report.
5. **Database concurrency:** SQLite is suitable for the current demo and test profile. For concurrent production writers or multiple API instances, select a server database, implement environment-based connection configuration and migrations, and test transaction/isolation behavior.
6. **Export size:** Employee/salary CSV export currently materializes result rows and the output string. Large exports can consume significant memory; use bounded exports or streamed responses if production export sizes demand it.

## Security and operational performance

- Production mode refuses to start without a sufficiently long configured signing secret. Bootstrap credentials are required only until an admin exists; development demo accounts are not created in production mode.
- Production still needs secret rotation, HTTPS, backup/restore, database access controls, monitoring, audit retention, and deployment-specific rate/size limits.
- Avoid logging credentials, bearer tokens, raw salary data, or complete uploaded files.
- Treat performance data as environment-specific; establish representative load tests before setting capacity targets.
