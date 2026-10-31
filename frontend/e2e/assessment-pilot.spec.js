import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;

test('50-post assessment pilot preview reads campaign captures without paid provider calls', async({page,request})=>{
  const paid=[];
  page.on('request',req=>{if(/socialcrawl\.dev|api\.openai\.com/.test(req.url()))paid.push(req.url())});
  const auth=await request.post('/api/auth/login',{data:{email,password}});
  expect(auth.ok()).toBeTruthy();
  const token=(await auth.json()).access_token;
  const headers={Authorization:'Bearer '+token};
  const created=await request.post('/api/functions/socialListening',{
    headers,data:{action:'createCampaign',data:{
      name:'QA Pilot '+Date.now(),primary_keywords:['pemilu'],platforms:['tiktok'],
      description:'Synthetic browser QA campaign; no provider actions permitted.'
    }}
  });
  expect(created.ok()).toBeTruthy();
  const campaign=(await created.json()).campaign;
  const response=await request.post('/api/functions/socialListening',{
    headers,data:{action:'campaignAssessmentPilotPreview',id:campaign.id,
      data:{sample_size:50}}
  });
  expect(response.ok()).toBeTruthy();
  const pilot=await response.json();
  expect(pilot.requested).toBe(50);
  expect(pilot.total).toBe(0);
  expect(pilot.records).toEqual([]);
  expect(pilot.paid_provider_called).toBe(false);
  expect(pilot.cost_note).toMatch(/0 AI and 0 crawl credits/i);
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/^password$/i).fill(password);
  await page.getByRole('button',{name:/log in|masuk/i}).click();
  await page.waitForURL(url=>!url.pathname.startsWith('/login'));
  await page.goto('/social-listening/campaigns/'+campaign.id);
  await expect(page.getByRole('navigation',{name:'Selected campaign sections'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Captured Posts'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Candidate Watchlist'})).toBeVisible();
  expect(paid).toEqual([]);
});
