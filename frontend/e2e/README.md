# E2E smoke

Read-only Playwright smoke tests for the pilot UI. They verify login, `/safety`,
the six permission-based tabs and safe default settings.

## Requirements

- Node.js 22+;
- Microsoft Edge (`channel: msedge`) or change the channel in
  `playwright.config.ts`;
- a pilot demo account with safety permissions.

## Run

```powershell
$env:PILOT_LOGIN = '<school-admin-login>'
$env:PILOT_PASSWORD = '<school-admin-password>'
npm run test:e2e
```

Optional:

```powershell
$env:PILOT_BASE_URL = 'https://school-platform-v2.alwaysdata.net'
```

The setup project writes the authenticated browser state to
`e2e/.auth/user.json`. The directory is gitignored and must never be committed.
If `PILOT_LOGIN` or `PILOT_PASSWORD` is missing, the setup and dependent tests
are skipped.
