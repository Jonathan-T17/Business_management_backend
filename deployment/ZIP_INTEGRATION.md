# ZIP integration review

Source: `New folder (3).zip`. Reviewed against the repaired project; its overwrite
script was not executed.

| ZIP content | Decision |
| --- | --- |
| Field-operation serializers | Merged removal of the superuser cross-company bypass. Added checks for partial updates and platform identities with a company assigned. |
| Related field-stop lookup | Uses the same visibility policy as field activities, so direct reads and updates cannot bypass the serializer restriction. |
| Root URLs | All 31 route definitions already match; retained the current ordering and comments. |
| Company-setup serializers | Already identical; no replacement needed. |
| Production settings and Docker files | Kept the repaired storage, static asset, dependency, build-path, and worker configuration. |
| Requirements | Kept Django 6 and the existing dependency files. Required production packages are already covered; unused monitoring/cache packages were not added. |
| Environment example | Already identical. |
| Runbook | Kept the current expanded upgrade and login instructions. |
| Patch and contract scripts | Not copied. The patch script overwrites whole files; the contract script assumes absent `backend_overlay` and `frontend` directories. Backend contract tests cover the available project. |
| Diff files and patch notes | Used as review material, not applied as a second patch. |
| Compiled Python files | Not imported. |

This integration does not change the database schema or downgrade Django. The
database migrations prepared during the earlier repair remain a separate upgrade
step described in `RUNBOOK.md`.
