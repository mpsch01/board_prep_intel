# DEFERRED-YOY-ROBUSTNESS deferred flag

**Session:** BATON 050 (2026-04-08)  
**Context:** Practice Q year-over-year analysis refinements

## What happened
In BATON 050, the year-over-year section (Section 3b) was added to ite_report_builder_v2.js with longitudinal trend data and month-by-month aggregation. Preliminary testing shows the core logic works, but the month-by-month rollup has some edge cases:

- Months with 0 questions don't display cleanly
- Year transitions (e.g., Nov 2024 → Jan 2025) can cause trend discontinuities
- The aggregation logic assumes uniform question distribution across months (not always true)

## Deferred action
Further robustness testing is needed when Mikey provides multi-year practice Q sets with dense temporal coverage. Current implementation is usable for exploratory analysis but may need refactoring for production dashboards.

## Flag lifecycle
- **DEFERRED-YOY-ROBUSTNESS** remains ACTIVE in project_session_log.md
- Review in next housekeeping session after more real-world test data arrives
