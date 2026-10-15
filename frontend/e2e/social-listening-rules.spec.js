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
  await page.goto('/social-listening?tab=search');

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
  await page.goto('/social-listening?tab=search');

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
  await page.goto('/social-listening?tab=search');

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
  await page.goto('/social-listening?tab=search');
  const sources=['Instagram','Youtube','X / Twitter','Threads','Reddit','Linkedin','Online News'];
  for(const label of sources){const cb=page.getByRole('checkbox',{name:label,exact:true});if(await cb.isChecked())await cb.uncheck();}
  const tiktok=page.getByRole('checkbox',{name:'Tiktok',exact:true});if(!(await tiktok.isChecked()))await tiktok.check();
  await expect(page.getByText(/1 credits?/i).first()).toBeVisible();
  await expect(page.getByRole('button',{name:/Search SocialCrawl.*1 credits?/i})).toBeVisible();
});


// Architecture v2 campaign-first entry point, stored configuration, and no paid crawls.
test('Monitoring campaigns are saved as drafts and survive reload without provider calls',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');
  await expect(page.getByRole('heading',{name:'Monitoring Campaigns'})).toBeVisible();
  const name='QA Campaign '+Date.now();
  await page.getByRole('button',{name:/New Campaign/i}).click();
  await page.getByLabel(/Campaign name/i).fill(name);
  await page.getByRole('textbox',{name:'Main keywords'}).fill('pemilu');
  await page.getByRole('textbox',{name:'Main keywords'}).press('Enter');
  await page.getByRole('textbox',{name:'Main keywords'}).fill('gibran');
  await page.getByRole('textbox',{name:'Main keywords'}).press('Enter');
  await page.getByRole('textbox',{name:'Secondary keywords'}).fill('wapres');
  await page.getByRole('textbox',{name:'Secondary keywords'}).press('Enter');
  await page.getByLabel(/Excluded keywords/i).fill('concert');
  await page.getByRole('button',{name:'Save Draft'}).click();
  await expect(page.getByRole('status')).toContainText('Campaign saved as draft');
  await expect(page.locator('article.intel-card').filter({hasText:name})).toBeVisible();
  await page.reload();
  const card=page.locator('article.intel-card').filter({hasText:name});
  await expect(card).toBeVisible();
  await expect(card).toContainText('Draft');
  await expect(card).toContainText('pemilu, gibran');
  await expect(card).toContainText('Runs: 0');
  await card.getByRole('button',{name:'Pause'}).click();
  await expect(card).toContainText('Paused');
});


test('Campaign schedule panel shows estimates and no automatic paid crawling',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');
  const name='QA Schedule '+Date.now();
  await page.getByRole('button',{name:/New Campaign/i}).click();
  await page.getByLabel(/Campaign name/i).fill(name);
  await page.getByRole('textbox',{name:'Main keywords'}).fill('bawaslu');
  await page.getByRole('textbox',{name:'Main keywords'}).press('Enter');
  await page.getByRole('button',{name:'Save Draft'}).click();
  const card=page.locator('article.intel-card').filter({hasText:name});
  await expect(card).toBeVisible();
  await card.getByRole('button',{name:'View'}).click();
  const schedule=page.getByLabel('Campaign schedule and crawl history');
  await expect(schedule).toBeVisible();
  await expect(schedule).toContainText('Estimated credits per run:');
  await expect(schedule).toContainText('Last successful crawl:');
  await expect(schedule).toContainText('No collection runs recorded for this campaign');
  await expect(schedule).toContainText('Automatic paid crawling disabled pending explicit approval');
});


test('Campaign keyword tags support Enter, deduplication, removal and preserved phrase input',async({page})=>{
  await uiLogin(page);
  await page.goto('/social-listening');
  await page.getByRole('button',{name:/New Campaign/i}).click();
  const dialog=page.getByRole('dialog');
  const main=dialog.getByRole('textbox',{name:'Main keywords'});
  const secondary=dialog.getByRole('textbox',{name:'Secondary keywords'});
  await main.fill('money politics');await main.press('Enter');
  await expect(dialog.getByText('money politics',{exact:true})).toBeVisible();
  await main.fill('MONEY POLITICS');await main.press('Enter');
  await expect(dialog.getByRole('button',{name:'Remove money politics from Main keywords'})).toHaveCount(1);
  await secondary.fill('election oversight');await dialog.getByRole('button',{name:'Add'}).last().click();
  await expect(dialog.getByText('election oversight',{exact:true})).toBeVisible();
  await dialog.getByRole('button',{name:'Remove money politics from Main keywords'}).click();
  await expect(dialog.getByText('money politics',{exact:true})).toHaveCount(0);
  await expect(dialog.getByRole('button',{name:'Save Draft'})).toBeDisabled();
});
