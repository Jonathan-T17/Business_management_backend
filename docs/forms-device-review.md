# Forms device review - 4 October 2026

## Completed locally

- Dedicated full-form preview with Back to library and Choose this form actions.
- Keyboard focus moves into the preview and returns to its original card.
- Preview scrolling keeps the Back button below the fixed header.
- Item-removal controls enlarged to 44-pixel minimum height.
- All 23 library templates checked in the in-app browser at 390x844, 768x1024 and 1280x900 in dark mode, plus 768x1024 in light mode: 92 layout checks, no horizontal overflow or clipped input controls.
- Representative collection forms checked at 320x740 and 844x390; item rows and dropdown changes exercised in preview only.
- Shared input text is 16px. This helps mobile readability; it does not constitute an iOS zoom or keyboard test.
- Representative tablet and phone views inspected visually. These were viewport checks in one desktop browser engine, not physical device certification.
- Raw measurements: forms-responsive-checks.json.

## Required before production release

Use a staging company and disposable test entries on real Android Chrome and iOS Safari, plus desktop Chrome/Edge/Firefox/Safari where available.

1. Browse every library category, preview complete forms, return to the same card and select a company draft.
2. Review fields and reviewer destination; publish ordinary and restricted forms using authorized test accounts.
3. With employee and manager accounts, verify form availability, identity/date/location defaults, and company isolation.
4. On phones and tablets, check portrait/landscape, native keyboards, date/time pickers, dropdowns, text zoom, and 200% browser zoom. Ensure focused fields and actions remain reachable with the keyboard open.
5. Enter long notes, multiple items, decimals, empty required fields and invalid values. Confirm clear errors, draft recovery and retry behavior on a slow/interrupted connection.
6. Submit several entries of the same form on one date for different locations. Verify separate records, review routing, approvals and returned corrections.
7. Confirm preview answers never create work entries. Confirm confidential answers and approval authority remain restricted.
8. Check screen-reader labels, required/optional states, keyboard navigation and light/dark contrast on actual devices.

The production release remains pending these real-device and populated workflow checks.
