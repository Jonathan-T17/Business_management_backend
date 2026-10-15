# Guided setup actions and unfinished work

14 October 2026. This is a focused follow-up to the system readiness review, not deployment certification.

The embedded setup layout hid entire page headers, including their creation actions. It now hides the repeated heading while preserving actions. Signed-in verification confirmed that New team is reachable from guided setup without leaving the journey. The same shared correction preserves embedded department and position header actions.

Department and team creation now register unfinished work with the setup journey. Switching between these sections and confirming the setup step is blocked until changes are resolved. Their close controls and normal navigation use the shared unfinished-work warning, with no automatic save. Mutation-in-progress navigation is blocked. Team creation now has persistent associated labels and visible failure feedback.

Company profile edits also register unfinished work, use the shared leave/cancel warning, and disable details while saving. No company access, role, permission, activation or server-side validation rules changed.

Verification: targeted lint and frontend TypeScript checks passed. In the signed-in company session, opened the completed departments/teams step for editing, verified restored New team action and field labels, entered a synthetic team name, confirmed the close warning and disabled setup continuation, then discarded it. No live team, department, company profile or setup completion was saved.

Evidence: [restored setup actions](setup-actions-restored-2026-10-14.png), [unfinished-work warning](setup-draft-protection-2026-10-14.png).

Remaining checks include headquarters/branch editor transitions, invitations and other setup subflows, collection error/pagination coverage and broader device checks. The shared browser-history guard depends on browser navigation API support; physical-device and unsupported-browser behavior still require staging verification. Real infrastructure checks remain open.
