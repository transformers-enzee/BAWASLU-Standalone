import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = 'admin@bawaslu.local';
const ADMIN_PASSWORD = 'ChangeMeNow!';
const ANALYST_EMAIL = 'qa.bali.analyst@example.com';
const ANALYST_PASSWORD = 'QaOnlyPassword123!';

async function apiLogin(request, email, password) {
  const response = await request.post('/api/auth/login', { data: { email, password } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token;
}

async function ensureAnalyst(request) {
  const register = await request.post('/api/auth/register', {
    data: { email: ANALYST_EMAIL, password: ANALYST_PASSWORD, full_name: 'QA Bali Analyst' },
  });
  expect([200, 409]).toContain(register.status());

  const adminToken = await apiLogin(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const list = await request.post('/api/functions/registry', {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { action: 'users', data: {} },
  });
  expect(list.ok()).toBeTruthy();
  const payload = await list.json();
  const analyst = payload.users.find((u) => u.email === ANALYST_EMAIL);
  expect(analyst).toBeTruthy();

  const assignment = await request.post('/api/functions/registry', {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: {
      action: 'setUser',
      id: analyst.id,
      data: {
        access_role: 'Provincial Analyst',
        geographic_scope: 'Province',
        province: 'Bali',
        regency_city: '',
        status: 'Active',
        permissions: {
          view_intelligence: true,
          add_intelligence: true,
          edit_intelligence: true,
          review_ai_suggestions: true,
          human_validation: false,
          verify_evidence: false,
          manage_watchlist: false,
          upload_evidence: true,
          manage_users: false,
          administration: false,
        },
      },
    },
  });
  expect(assignment.ok()).toBeTruthy();
}

async function uiLogin(page, email, password) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/^password$/i).fill(password);
  await page.getByRole('button', { name: /log in|masuk/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
}

test.beforeEach(async ({ request }) => {
  await ensureAnalyst(request);
});

test('national administrator sees governance modules and cannot edit own assignment', async ({ page }) => {
  await uiLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);

  await expect(page.getByRole('link', { name: /data sources/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /validation/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /administration/i })).toBeVisible();

  await page.getByRole('link', { name: /administration/i }).click();
  await expect(page.getByRole('heading', { name: /user access management/i })).toBeVisible();
  await expect(page.getByText(/your own access assignment cannot be changed/i)).toBeVisible();
});

test('provincial analyst only sees permitted navigation and protected routes are denied', async ({ page }) => {
  await uiLogin(page, ANALYST_EMAIL, ANALYST_PASSWORD);

  await expect(page.getByRole('link', { name: /intelligence inbox/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /intelligence assistant/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /add intelligence/i })).toBeVisible();

  await expect(page.getByRole('link', { name: /data sources/i })).toHaveCount(0);
  await expect(page.getByRole('link', { name: /validation/i })).toHaveCount(0);
  await expect(page.getByRole('link', { name: /administration/i })).toHaveCount(0);

  for (const route of ['/sources', '/validation', '/administration']) {
    await page.goto(route);
    await expect(page.getByRole('alert')).toContainText(/access denied/i);
  }
});

test('logout returns the user to login and clears authenticated access', async ({ page }) => {
  await uiLogin(page, ANALYST_EMAIL, ANALYST_PASSWORD);

  await page.getByRole('button', { name: /log out|keluar/i }).click();
  await page.waitForURL(/\/login/);
  await expect(page.getByRole('button', { name: /log in|masuk/i })).toBeVisible();

  await page.goto('/inbox');
  await page.waitForURL(/\/login/);
});

test('language toggle switches app-owned navigation labels', async ({ page }) => {
  await uiLogin(page, ANALYST_EMAIL, ANALYST_PASSWORD);

  await page.getByRole('button', { name: 'ID' }).click();
  await expect(page.getByRole('link', { name: /kotak masuk intelijen/i })).toBeVisible();

  await page.getByRole('button', { name: 'EN' }).click();
  await expect(page.getByRole('link', { name: /intelligence inbox/i })).toBeVisible();
});
