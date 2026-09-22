# Company setup and organisation structure

The required setup now has seven steps: company profile; locations/departments/teams;
positions/reporting lines; permissions/access; forms/processes; people/invitations;
and review/activation. Version 2 requires both new companies and companies that
completed the previous setup to review the expanded arrangement. Existing records
are retained. Profile and published-form readiness are recognised automatically.
Structure, positions, access and invitations require explicit review through the
completion API. Invitations can be deferred; invite acceptance never blocks setup.

At least one active location, one active position, a role preset and a published
form are required. Departments and teams are optional for small companies.
Existing company-scoped and system role templates are available as starting points.
Completing setup opens operational routes through the JWT setup gate.

## Position structure

Positions now have optional branch, department, team and reports-to-position links.
Company-wide departments may serve positions based at a branch. Department/team
placement and tenant ownership are validated; reporting loops are rejected.
The position editor supports saved-record editing and suggested titles, including
CEO, Operations, Finance, HR, branch managers and team members. Titles remain
company-unique: include location in a title when distinguishing equivalent posts.
Headquarters is represented as a named location under the company.

Location and reporting relationships do not automatically widen data visibility.
Existing capability and record-visibility rules remain authoritative. Employees
retain one primary position and may now hold multiple additional position
assignments, each company-wide or limited to selected locations. Access is additive:
a branch-limited assignment does not remove primary, direct or administrator grants.

Selected-location assignments support USE_FORMS, SUBMIT_FORMS,
VIEW_FORM_SUBMISSIONS, REVIEW_SUBMISSIONS, VIEW_ALL_REPORTS and
VIEW_COMPANY_ANALYTICS. Unsupported administrative/confidential permissions cannot
be included in a branch-limited position. Company-wide additional positions support
the normal permission catalogue and sensitive-delegation rules. Runtime filtering
also excludes malformed sensitive grants from branch-limited assignments.

Position routing and scheduled reporting include active additional assignments
within the target location. Revocation/suspension removes inherited capabilities;
position-based workflow participants are rechecked before acting or reading through
that relationship. Existing author/direct/delegated permissions remain independent.
Analytics overview is location-filtered for branch-only analytics grants, while
company-wide analytics snapshots and AI endpoints require company-wide authority.
The setup People and access page manages additional assignments and revocation.
No existing company assignments are changed by the schema migration.

## Access and invitations

The People and access page displays the permission catalogue and assigns a saved
role's capabilities to a position through an atomic replacement endpoint. This
updates actual PositionCapabilityGrant records, rather than merely creating a role
template. Editing a template does not automatically change assigned permissions.
Sensitive position grants now use the same validation as setup role templates:
actors cannot delegate sensitive capabilities they do not possess. Platform-only
capabilities cannot be assigned by a tenant.

Invitations can specify an active company position. Acceptance assigns an employee
profile to that position and its location, department and team. The invitation UI
supports up to 50 addresses sharing an assignment, sent sequentially, with failed
addresses retained for retry. No invitations were sent during implementation.
An invitation without a position retains the previous behaviour. Employee access
uses the position's current grants; later changes affect position holders.

## Forms and analytics

Forms are saved as drafts and explicitly published after review. Published forms
are available to eligible users; responses remain separate submissions. Approval
workflows use their actual is_active field. Empty comma-separated choice entries
are removed on save; empty choice questions show a specific validation message.

Company admins receive operational analytics by default. Charts use visible records,
not unrestricted confidential answers. The activity chart uses the latest 30 active
dates, not numeric aggregation of arbitrary custom form fields.

## Verification

The focused setup, position, invitation, workflow and strict schema selection passed
13 tests before the final batch-invitation UI change. Browser verification showed
an existing company at 29% (profile and published form retained), with organisation
structure selected next. Production frontend build and TypeScript passed before
the final batch-invitation UI change. Final checks are recorded in the task response.

Final validation: frontend production build (including TypeScript), changed-screen
ESLint, migration consistency and diff whitespace checks passed. The tests directory
run passed 147 tests with one outdated expected setup destination; after updating
the expected destination list, all five setup-route tests passed. The 13-test
focused selection included strict schema generation, tenant boundaries, reporting
cycle prevention, atomic access updates, and invitation position inheritance.
Browser verification confirmed the seven-step dashboard and location/department/
team/reporting controls, without changing live company structure or access.


## Additional-position verification (2026-09-21)

The tests directory run passed all 153 tests. That run emitted a test-database
teardown warning because a follow-up test process overlapped its cleanup; the
follow-up completed cleanly with 10 position/workflow tests passing. Frontend
production build and TypeScript passed; final changed-screen ESLint passed.
Strict schema generation is included in the backend tests. Migration consistency
and whitespace checks passed. Browser verification confirmed the assignment panel
and its employee/position empty-state guidance. No live employee access was changed.

## Company overview landing (2026-09-21)

The administrator dashboard now presents saved locations, departments and positions,
including reporting labels and company-level positions. Empty structures show explicitly
labelled examples, never fabricated saved records. Setup remains mandatory; the landing
page shows progress and the next step while operational pages remain gated. After setup,
the structure overview appears alongside the existing daily operations and analytics.
The permissions step explains administrator and CEO responsibilities and explicit
confidential-data access. Ownership is explained as a business responsibility only:
a distinct system owner role, ownership transfer, and persisted responsibility selection
have not been implemented. Existing permission grants are unchanged.
