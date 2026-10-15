# Requests and Field Work collection completeness

14 October 2026. Focused follow-up to the system readiness review. No live requests, activities or company configuration were created or changed.

Requests and Field Work now expose Previous/Next page controls using the server’s totals. They request numbered pages through fixed same-origin API endpoints rather than following next-page URLs. Request search resets to page one, searches titles and references on the server, and preserves the existing visibility queryset and global filters/ordering. Query keys include company and account identity.

Field Work now separates loading, retryable failures and genuinely empty results, shows readable status/type labels and activity dates, and identifies the number available versus the number on the page. The inaccurate Today’s heading was removed because the list includes other dates. Field Work is now grouped separately from company administration in workspace navigation.

Verification: frontend type checks and targeted lint passed for the collection changes. The pagination contract test loads the real API modules and shared response adapter, checking totals, filters, explicit page numbers, fixed endpoints and compatibility with array responses. An isolated backend regression verifies 26 owned requests across two distinct pages, title/reference search and exclusion of peer-private and foreign-company requests. Signed-in browser checks verified the genuine empty Requests and Field Work states; no live records were added to populate pages. Error presentation and multi-page behavior were not live-browser tested against company records.

Evidence: [Field Work state](field-work-states-2026-10-14.png). Tests: `tests/contracts/workspace_collection_pages.cjs` and `tests/security/test_request_collection_search.py`.

This batch does not certify the entire system. Remaining coverage includes subscription and notification policy screens, other optional-module error/pagination states, browser/device behavior and real staging infrastructure verification.
