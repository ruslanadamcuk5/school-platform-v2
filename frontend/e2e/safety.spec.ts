import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const tabs = [
  'Мои обращения',
  'Обращения школы',
  'Инциденты',
  'Согласия',
  'Геолокация',
  'Настройки',
];

type BrowserErrors = {
  console: string[];
  page: string[];
  http: string[];
};

function watchErrors(page: Page): BrowserErrors {
  const errors: BrowserErrors = { console: [], page: [], http: [] };

  page.on('console', (message) => {
    if (message.type() === 'error') {
      errors.console.push(message.text());
    }
  });
  page.on('pageerror', (error) => {
    errors.page.push(error.message);
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      errors.http.push(`${response.status()} ${response.url()}`);
    }
  });

  return errors;
}

function expectNoBrowserErrors(errors: BrowserErrors) {
  expect(errors.console).toEqual([]);
  expect(errors.page).toEqual([]);
  expect(errors.http).toEqual([]);
}

test('safety service is enabled and all permitted tabs are visible', async ({
  page,
}) => {
  const errors = watchErrors(page);

  await page.goto('/safety', { waitUntil: 'networkidle' });
  await expect(
    page.getByRole('heading', { name: 'Поддержка и безопасность' }),
  ).toBeVisible();
  await expect(
    page.getByText('сервис включён', { exact: false }).first(),
  ).toBeVisible();

  for (const tab of tabs) {
    await expect(page.getByRole('button', { name: tab, exact: true })).toBeVisible();
  }

  expectNoBrowserErrors(errors);
});

test('settings keep geolocation disabled and anonymous appeals enabled', async ({
  page,
}) => {
  const errors = watchErrors(page);

  await page.goto('/safety', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Настройки', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Сохранить настройки', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('switch', { name: 'Геолокация', exact: true }),
  ).toHaveAttribute('aria-checked', 'false');
  await expect(
    page.getByRole('switch', { name: 'Анонимные обращения', exact: true }),
  ).toHaveAttribute('aria-checked', 'true');
  await expect(
    page.getByText('Текущая конфигурация', { exact: false }).first(),
  ).toContainText('365');

  expectNoBrowserErrors(errors);
});
