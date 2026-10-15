# Suspended-company sign-in message review

15 October 2026. Diagnostic check only; authentication and displayed wording were not changed.

The sign-in endpoint rejects a user belonging to an inactive company with HTTP 400. The API error envelope's message is `One or more fields are invalid.` Its `fields.non_field_errors` contains `This account or company is inactive.`

The actual `getErrorMessage` function from the frontend sign-in component returns the envelope message before inspecting validation details. Running that function against this response confirmed that the displayed message is **One or more fields are invalid.** This is confusing because it appears to blame the email/password fields instead of explaining company suspension.

Suggested wording for a future change: **Your company workspace is suspended. Contact your company administrator or platform support.** Any more specific account/company-status explanation should be returned only after verifying credentials, rather than exposing status based on an email address alone. Archived and individually disabled accounts need their own appropriate explanation.

The response was exercised using isolated synthetic company-admin and employee accounts. No real workspace was suspended and no signed-in account was changed.
