import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

// Self-hosted, temporary SQLite test backend. NEVER point this test at live
// Render or Supabase. No officer or customer records are created or mutated.
const ADMIN_EMAIL='admin@bawaslu.local';
const ADMIN_PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

test.beforeEach(async ({}, testInfo) => {
  if (process.env.PLAYWRIGHT_BASE_URL || !ADMIN_PASSWORD) {
    testInfo.skip(true,'Read-only pilot must use the isolated local test server');
  }
});

async function signIn(page) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/^password$/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test('unauthenticated officer workspaces redirect to login',async ({page})=>{
  for (const route of ['/smart-radar','/inbox','/assistant','/social-listening']) {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login\?/);
    await expect(page.getByLabel(/email/i)).toBeVisible();
  }
});

test('authenticated read-only workspaces load without route errors or paid client calls',async ({page})=>{
  const paid=[];
  const errors=[];
  page.on('request',req=>{
    if (/api\.openai\.com|socialcrawl\.dev/i.test(req.url())) paid.push(req.url());
  });
  page.on('pageerror',err=>errors.push(err.message));
  await signIn(page);
  const routes=['/','/smart-radar','/social-listening','/inbox','/assistant','/command-center'];
  for (const route of routes) {
    const response=await page.goto(route);
    expect(response?.status()||200).toBeLessThan(500);
    await expect(page.getByRole('button',{name:/log out|keluar/i})).toBeVisible();
    await expect(page.locator('body')).not.toContainText(/uncaught runtime error|application error|page not found/i);
  }
  expect(paid).toEqual([]);
  expect(errors).toEqual([]);
});

test('navigation exposes the four operational workspaces under officer permissions',async ({page})=>{
  await signIn(page);
  const nav=page.locator('nav');
  for(const href of ['/smart-radar','/social-listening','/inbox']) {
    await expect(nav.locator('a[href="'+href+'"]').first()).toBeVisible();
  }
  // Single AI-5 entry is role-aware: leadership uses Management AI-5,
  // while operational officers use the Operational AI-5 route.
  const assistant=nav.locator('a[href="/ai-5"], a[href="/management/ai-5"]');
  await expect(assistant).toHaveCount(1);
  await expect(assistant.first()).toBeVisible();
  await expect(nav.locator('a[href="/ai-assistant"], a[href="/ai-4"]')).toHaveCount(0);
  await page.goto('/smart-radar');
  await expect(page.getByRole('button',{name:/Reports & Briefings|Laporan & Ringkasan/})).toBeVisible();
});

test('staging-like health metadata matches displayed shell build version',async ({page,request})=>{
  const response=await request.get('http://127.0.0.1:8000/api/health');
  expect(response.ok()).toBeTruthy();
  const health=await response.json();
  expect(health.ok).toBe(true);
  expect(typeof health.build_version).toBe('string');
  await signIn(page);
  await expect(page.locator('aside')).toContainText('Build '+health.build_version);
});
