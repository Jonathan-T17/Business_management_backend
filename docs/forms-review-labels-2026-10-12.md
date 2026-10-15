# Clearer form-review labels — 12 October 2026

The live journey showed that review cards and details used only the workflow name.
Different forms sharing that workflow were therefore difficult to distinguish.

Form-submission reviews now use the form name saved in the entry's schema snapshot
as their heading. The frontend retains the workflow name separately as Review route
on cards and in details. Other target types retain their previous heading behavior;
missing/malformed form names fall back to the workflow name. Employee-entered entry
titles and answer data are not added to the review summary. Target type and company
are checked before using form metadata; endpoint participant and tenant filtering
remains unchanged.

Live verification: the approved manager review /approvals/8 displays TEST - Forms
journey 12 October 2026 as the heading and TEST - Food Production report review as
the separate route. At 390×844 it has no horizontal overflow. Screenshot:
forms-review-title-implemented.jpg. No new entry, decision or permission change was
made while checking these labels.

TypeScript and targeted frontend lint passed. The full correction-cycle regression
was expanded to check the form heading, preserved route name, hidden private entry
title, and denied review access for unrelated colleagues and another company.

Production scanner detection and physical-phone checks remain pending as documented
in forms-upload-release-checks-2026-10-12.md. This improvement does not require those
environments and does not claim to complete their verification.

Final result: the expanded end-to-end correction-cycle regression passed in 82.27 seconds, including the new review-label and privacy assertions.
