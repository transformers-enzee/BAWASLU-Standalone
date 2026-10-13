import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const ADMIN_EMAIL='admin@bawaslu.local';
const ADMIN_PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

async function uiLogin(page){
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/^password$/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}

test('saved Social Listening search can pause resume and load filters without provider calls',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');

  const name='QA Saved Search '+Date.now();
  await page.getByLabel(/keyword/i).fill('bawaslu qa');
  await page.getByPlaceholder(/saved search name/i).fill(name);
  await page.getByRole('button',{name:/save search/i}).click();

  await page.getByRole('button',{name:/saved searches/i}).click();
  const card=page.locator('.intel-card').filter({hasText:name});
  await expect(card).toBeVisible();
  await expect(card.getByText('Active',{exact:true})).toBeVisible();
  await expect(card.getByText('Mine',{exact:true})).toBeVisible();
  await expect(card.getByText(/Created by:/i)).toBeVisible();
  await expect(card.getByText(/Scope:/i)).toBeVisible();

  await card.getByRole('button',{name:/pause/i}).click();
  await expect(card.getByText('Inactive',{exact:true})).toBeVisible();

  await card.getByRole('button',{name:/resume/i}).click();
  await expect(card.getByText('Active',{exact:true})).toBeVisible();

  await card.getByRole('button',{name:/load filters/i}).click();
  await expect(page.getByLabel(/keyword/i)).toHaveValue('bawaslu qa');
});


test('saved Social Listening search can edit and delete without provider calls',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');

  const original='QA Lifecycle '+Date.now();
  const renamed=original+' Renamed';
  await page.getByLabel(/keyword/i).fill('bawaslu lifecycle');
  await page.getByPlaceholder(/saved search name/i).fill(original);
  await page.getByPlaceholder(/saved search description/i).fill('Initial QA description');
  await page.getByRole('button',{name:/save search/i}).click();

  await page.getByRole('button',{name:/saved searches/i}).click();
  let card=page.locator('.intel-card').filter({hasText:original});
  await expect(card).toBeVisible();
  await card.getByRole('button',{name:/edit/i}).click();

  await expect(page.getByText(/Editing saved search/i)).toBeVisible();
  await page.getByPlaceholder(/saved search name/i).fill(renamed);
  await page.getByPlaceholder(/saved search description/i).fill('Updated QA description');
  await page.getByRole('button',{name:/update saved search/i}).click();

  card=page.locator('.intel-card').filter({hasText:renamed});
  await expect(card).toBeVisible();
  await expect(card.getByText('Updated QA description')).toBeVisible();

  page.once('dialog',dialog=>dialog.accept());
  await card.getByRole('button',{name:/delete/i}).click();
  await expect(page.locator('.intel-card').filter({hasText:renamed})).toHaveCount(0);
});


test('Social Listening date filters are mutually exclusive without provider calls',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');

  const lookback=page.getByLabel(/lookback days/i);
  const dateFrom=page.getByLabel(/date from/i);
  const dateTo=page.getByLabel(/date to/i);

  await expect(lookback).toHaveValue('7');
  await dateFrom.fill('2026-10-01');
  await expect(lookback).toHaveValue('');
  await dateTo.fill('2026-10-08');
  await expect(dateFrom).toHaveValue('2026-10-01');

  await lookback.fill('14');
  await expect(dateFrom).toHaveValue('');
  await expect(dateTo).toHaveValue('');
});


test('Social Listening tabs persist through browser reload without running provider searches', async ({ page }) => {
  await uiLogin(page);
  await page.goto('/social-listening?tab=rules');
  await expect(page.getByRole('button', { name: /Saved Searches/i }).first()).toBeVisible();
  await expect(page).toHaveURL(/tab=rules/);
  await page.reload();
  await expect(page).toHaveURL(/tab=rules/);
  await page.getByRole('button', { name: /Review Queue/i }).first().click();
  await expect(page).toHaveURL(/tab=queue/);
  await page.reload();
  await expect(page).toHaveURL(/tab=queue/);
});


test('Review Queue refresh gives visible feedback without resetting filters', async ({ page }) => {
  await uiLogin(page);
  await page.goto('/social-listening?tab=queue');
  await expect(page.getByRole('button', { name: /Refresh queue/i })).toBeVisible();
  await page.getByRole('button', { name: /Refresh queue/i }).click();
  await expect(page.getByRole('status')).toContainText('Queue refreshed successfully.');
  await expect(page).toHaveURL(/tab=queue/);
});


test('TikTok only displays native one-credit estimate without provider execution',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');
  const sources=['Instagram','Youtube','X / Twitter','Threads','Reddit','Linkedin','Online News'];
  for(const label of sources){const cb=page.getByRole('checkbox',{name:label,exact:true});if(await cb.isChecked())await cb.uncheck();}
  const tiktok=page.getByRole('checkbox',{name:'Tiktok',exact:true});if(!(await tiktok.isChecked()))await tiktok.check();
  await expect(page.getByText(/1 credits?/i).first()).toBeVisible();
  await expect(page.getByRole('button',{name:/Search SocialCrawl.*1 credits?/i})).toBeVisible();
});
