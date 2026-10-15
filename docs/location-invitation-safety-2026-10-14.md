# Headquarters, branch and invitation setup

14 October 2026. Local follow-up to guided setup; no live company configuration, employee assignment or invitation was saved or sent.

Headquarters selection now explains that it designates the main office without moving employees, departments or teams. Office-detail editing explains that the existing workplace remains the same record. Branch and headquarters edits use the shared unfinished-work warning, and saving blocks navigation. Opening another branch editor is disabled while headquarters selection is unresolved. Successful headquarters saving clears the completed local choices.

Invitation drafts now track email rows, optional position assignment and expiry settings. The shared navigation/discard warning protects these choices even before an email address is entered. Discard resets the whole draft. After an entirely successful invitation attempt, position and expiry options return to their defaults; unsuccessful addresses retain their choices for correction. No invitation authority or access rules were expanded.

Verification: frontend TypeScript and targeted lint passed. All six existing isolated headquarters and invitation journey regression tests passed. Signed-in checks verified office-detail close warning, headquarters explanation and disabled parallel branch editors, invitation navigation warning with only an assignment choice, Stay preserving that choice, and explicit discard returning the form and setup continuation to their clean state. No live mutation buttons were used.

Evidence: [headquarters selection](headquarters-choice-2026-10-14.png), [invitation choices](invitation-draft-choices-2026-10-14.png).

Remaining: broader workspace loading/error/pagination review, remaining setup editor transitions and cross-browser/device verification. Real email delivery, malware scanning, private storage, workers and backup restore still require isolated staging checks. This batch does not certify deployment readiness.
