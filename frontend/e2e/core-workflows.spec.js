import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = 'admin@bawaslu.local';
const ADMIN_PASSWORD = 'ChangeMeNow!';
const ANALYST_EMAIL = 'qa.bali.analyst@example.com';
const ANALYST_PASSWORD = 'QaOnlyPassword123!';

async function loginToken(request, email, password) {
  const r = await request.post('/api/auth/login', { data: { email, password } });
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token;
}

async function registry(request, token, action, data = {}, id = null) {
  const r = await request.post('/api/functions/registry', {
    headers: { Authorization: `Bearer ${token}` },
    data: { action, data, id },
  });
  return r;
}

async function intelligence(request, token, action, data = {}, id = null) {
  const r = await request.post('/api/functions/intelligence', {
    headers: { Authorization: `Bearer ${token}` },
    data: { action, data, id },
  });
  return r;
}

async function ensureAnalyst(request) {
  const register = await request.post('/api/auth/register', {
    data: { email: ANALYST_EMAIL, password: ANALYST_PASSWORD, full_name: 'QA Bali Analyst' },
  });
  expect([200, 409]).toContain(register.status());

  const adminToken = await loginToken(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const users = await registry(request, adminToken, 'users');
  expect(users.ok()).toBeTruthy();
  const analyst = (await users.json()).users.find((u) => u.email === ANALYST_EMAIL);
  expect(analyst).toBeTruthy();

  const assign = await registry(request, adminToken, 'setUser', {
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
  }, analyst.id);
  expect(assign.ok()).toBeTruthy();
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

test('Data Sources create and edit persists without external provider calls', async ({ page }) => {
  await uiLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto('/sources');

  await page.getByRole('button', { name: /register source/i }).click();
  const form = page.locator('form');
  await form.getByLabel(/name/i).fill('Playwright QA Source');
  await form.getByLabel(/source type/i).selectOption('OFFICIAL_SOURCE');
  await form.getByLabel(/source status/i).selectOption('Active');
  await form.getByLabel(/province/i).selectOption({ label: 'Bali' });
  await form.getByLabel(/regency \/ city/i).selectOption({ label: 'Kabupaten Bangli' });
  await form.getByLabel(/description/i).fill('Automated QA source');
  await form.getByRole('button', { name: /save source/i }).click();

  await expect(page.getByText('Playwright QA Source')).toBeVisible();
  await expect(page.getByText(/Kabupaten Bangli, Bali/)).toBeVisible();

  await page.getByRole('button', { name: /edit source/i }).last().click();
  const edit = page.locator('form');
  await edit.getByLabel(/source status/i).selectOption('Inactive');
  await edit.getByRole('button', { name: /update source/i }).click();

  await expect(page.getByText('Playwright QA Source')).toBeVisible();
  await expect(page.getByText(/Inactive/i)).toBeVisible();

  await page.reload();
  await expect(page.getByText('Playwright QA Source')).toBeVisible();
  await expect(page.getByText(/Kabupaten Bangli, Bali/)).toBeVisible();
});

test('unresolved jurisdiction blocks final validation, confirmed jurisdiction allows it', async ({ page, request }) => {
  const adminToken = await loginToken(request, ADMIN_EMAIL, ADMIN_PASSWORD);

  const created = await intelligence(request, adminToken, 'create', {
    title: 'Playwright Validation Record',
    original_content: 'Synthetic local QA evidence only.',
    source_type: 'MANUAL_ENTRY',
    source_name: 'Playwright QA',
    platform: 'Web',
    evidence_type: 'OBSERVED',
    verification_status: 'UNVERIFIED',
    review_status: 'Pending Review',
    priority: 'Medium',
    jurisdiction_type: 'Unresolved',
  });
  expect(created.ok()).toBeTruthy();
  const record = (await created.json()).item;

  const blocked = await intelligence(request, adminToken, 'review', {
    decision: 'Validated as Relevant Intelligence',
    review_notes: 'QA',
  }, record.id);
  expect(blocked.status()).toBe(400);
  expect((await blocked.json()).detail).toMatch(/jurisdiction confirmation required/i);

  const confirm = await intelligence(request, adminToken, 'confirmJurisdiction', {
    jurisdiction_type: 'Province',
    province: 'Bali',
    regency_city: '',
  }, record.id);
  expect(confirm.ok()).toBeTruthy();

  await uiLogin(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto('/validation');
  await expect(page.getByText('Playwright Validation Record')).toBeVisible();

  const card = page.locator('article, section, div').filter({ hasText: 'Playwright Validation Record' }).last();
  await card.getByRole('combobox').last().selectOption({ label: 'Validated as Relevant Intelligence' });
  await card.getByRole('button', { name: /record decision/i }).click();

  await expect(page.getByText(/human validation decision saved/i)).toBeVisible();
});

test('non-final validation decisions require reviewer notes', async ({ request }) => {
  const adminToken = await loginToken(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const created = await intelligence(request, adminToken, 'create', {
    title: 'Playwright Notes Guard',
    original_content: 'Synthetic local QA evidence only.',
    source_type: 'MANUAL_ENTRY',
    evidence_type: 'OBSERVED',
    verification_status: 'UNVERIFIED',
    review_status: 'Pending Review',
    priority: 'Low',
    jurisdiction_type: 'Province',
    province: 'Bali',
    confirm_jurisdiction: true,
  });
  expect(created.ok()).toBeTruthy();
  const record = (await created.json()).item;

  const noNotes = await intelligence(request, adminToken, 'review', {
    decision: 'Request More Information',
    review_notes: '',
  }, record.id);
  expect(noNotes.status()).toBe(400);
  expect((await noNotes.json()).detail).toMatch(/reviewer notes are required/i);

  const withNotes = await intelligence(request, adminToken, 'review', {
    decision: 'Request More Information',
    review_notes: 'Need additional source context.',
  }, record.id);
  expect(withNotes.ok()).toBeTruthy();
});

test('Bali Provincial Analyst cannot access an out-of-scope intelligence record directly', async ({ page, request }) => {
  const adminToken = await loginToken(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const created = await intelligence(request, adminToken, 'create', {
    title: 'Playwright Out Of Scope Record',
    original_content: 'Synthetic local QA evidence only.',
    source_type: 'MANUAL_ENTRY',
    evidence_type: 'OBSERVED',
    verification_status: 'UNVERIFIED',
    review_status: 'Pending Review',
    priority: 'Medium',
    jurisdiction_type: 'Province',
    province: 'West Java',
    confirm_jurisdiction: true,
  });
  expect(created.ok()).toBeTruthy();
  const record = (await created.json()).item;

  await uiLogin(page, ANALYST_EMAIL, ANALYST_PASSWORD);
  await page.goto(`/intelligence/${record.id}`);
  await expect(page.getByRole('heading', { name: /access denied/i })).toBeVisible();
  await expect(page.getByText('Playwright Out Of Scope Record')).toHaveCount(0);
});
