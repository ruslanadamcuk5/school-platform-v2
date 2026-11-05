import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';

import { expect, test as setup } from '@playwright/test';

const authFile = join('e2e', '.auth', 'user.json');
const login = process.env.PILOT_LOGIN;
const password = process.env.PILOT_PASSWORD;

setup.skip(!login || !password, 'PILOT_LOGIN/PILOT_PASSWORD are required');

setup('authenticate school admin', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'networkidle' });
  await page.locator('input[autocomplete="username"]').fill(login!);
  await page.locator('input[autocomplete="current-password"]').fill(password!);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await page.waitForFunction(() => window.location.pathname !== '/login');
  await expect(page).not.toHaveURL(/\/login$/);

  mkdirSync(dirname(authFile), { recursive: true });
  await page.context().storageState({ path: authFile });
});
