# Company forms integration — approved direction

Approved by the user on 2 October 2026. Company setup prepares structure, reporting relationships and access, then company forms, then invitations. Business-sector selection is optional and does not block form selection.

## Implemented foundation

- Expanded the system library from four to 23 starter designs, covering reporting, materials requests/dispatch/receipt/returns, collections, expenses/purchasing, people, stock/assets and inspections/incidents.
- Searchable category cards and question previews support single-template adjustment or multi-template selection. Available in company setup and saved company forms.
- Atomic, tenant-owned selection creates editable drafts; repeated selection returns existing company forms without overwriting them. Invalid designs roll back the entire selection. Existing platform starter records are preserved by the seed migration.
- Company copies can adjust questions, required answers, instructions and question help. Help text is preserved in submission snapshots. Technical question identifiers are behind advanced settings.
- Position audiences complement existing people, account-role and organization restrictions. These restrictions intersect; they do not grant submission capability or confidential disclosure rights.
- Review-route controls support assigned supervisor, headquarters position, or supervisor followed by headquarters. Existing published forms retain their route; changing it creates a draft revision. Route configuration requires workflow management and publishing capabilities plus form-management access.
- Direct headquarters routing requires explicit permitted positions or people; removing that audience is rejected while retaining the generated direct route. Headquarters recipients must be active company-wide positions within this tenant.
- Supervisor resolution uses the explicit employee manager, then the primary position's saved reporting line. Inactive or unrelated-company recipients are excluded.

Migrations 0008 and 0009 applied locally. No live company form selection, employee grants, publication, workflow decisions or invitations were performed. Administrator browser review verified categories, cards, previews and editor loading. Proof: company-form-library.jpg in the task visualization directory.

Validation: 26 tests passed across form-library, governance, primary-position scope and populated approval/reporting contracts. Frontend type checking and targeted lint passed; Django system checks passed.

## Connected materials journeys

Structured items keep names, quantities and units together. System provenance is retained through copies and revisions; required items cannot be removed or changed into an unrelated field. Stage forms require explicit audiences and use confirmations rather than independent approval routes.

The approved request anchors dispatch, receipt and return. Final reviewers can approve reduced quantities. Dispatch cannot exceed approval; receipt cannot exceed its linked delivery; returns cannot exceed their linked receipt. Partial receipt stays open; returns reopen the remaining amount. Stable action references prevent duplicate accounting on retries. History records each actor with company isolation and existing position access retained.

Materials and deliveries has a workspace, a dashboard entry for users with forms access, and a link from available forms. Worker screens explain the review route. The editor warns when no reviewer resolves for the current user's location. Empty or inactive routes cannot be published; dynamic routes are checked again at submission using the actual submitter.

Migrations 0010-0013 applied locally. Nineteen materials, library and approval/reporting tests passed. Initial browser control timed out; the subsequent live acceptance below supersedes that limitation. Isolated API checks cover partial approval, dispatch, receipt, return, retries and cross-company denial.

## Live browser acceptance, 2 October 2026

Published four clearly marked TEST-only materials forms for existing Honore, Uwera and Jonathan accounts. Request/receipt/return are limited to Honore; headquarters dispatch is limited to Jonathan. No account capability or position grants changed. A two-step USER review resolved Uwera then Jonathan, with workflow email notifications disabled. The dispatch test form was revised to headquarters scope instead of the requesting branch.

Browser submission a48ae819-2c15-424a-a371-343f192bc29a: requested 10 synthetic paper boxes; headquarters approved 6; dispatch/receipt of 5 stayed partial; final dispatch/receipt of 1 completed it. Returning 1 reopened fulfillment, and replacement dispatch/receipt completed it again. Totals: requested 10, approved 6, sent 7, received 7, returned 1. Uwera can inspect progress/history but has no dispatch/receipt/return controls.

The live test exposed and fixed two frontend omissions: materials approval/save buttons needed type=submit, and receipt/return required a visible linked movement selector. Native date keyboard entry worked; browser automation fill did not persist the date, so this was not treated as evidence of an application date-input defect. Test records remain clearly labelled, with no real inventory or financial entries.

Proof: materials-completed-browser-journey.jpg in the task visualization directory.

## Materials usability verification

The completed request opens from the populated workspace list. Progress distinguishes gross received quantities from quantities kept after returns, and shows the amount still due. Receipt and return choices exclude fully consumed movements; linked choices show remaining quantities. Action inputs display their available amount and limit entry accordingly, while backend quantity validation remains authoritative. History displays item quantities and linked action numbers. Accounts with no available actions see an explanatory message instead of an unusable action form.

Verified Honore's return selector excludes the receipt already returned. Selecting the original receipt enables its quantity input with a maximum of 5 boxes. The existing completed fixture remains unchanged at 6 boxes kept and 0 still due. Frontend type checking and targeted lint passed. Proof: materials-remaining-verified.jpg in the task visualization directory.
