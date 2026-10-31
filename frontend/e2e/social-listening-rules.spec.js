import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
async function login(page){
 await page.goto('/login');
 await page.getByLabel(/email/i).fill(email);
 await page.getByLabel(/^password$/i).fill(password);
 await page.getByRole('button',{name:/log in|masuk/i}).click();
 await page.waitForURL(url=>!url.pathname.startsWith('/login'));
}
async function makeCampaign(request, name){
 const auth=await request.post('/api/auth/login',{data:{email,password}});
 expect(auth.ok()).toBeTruthy();
 const token=(await auth.json()).access_token;
 const created=await request.post('/api/functions/socialListening',{
  headers:{Authorization:'Bearer '+token},
  data:{action:'createCampaign',data:{
    name,primary_keywords:['gibran'],platforms:['tiktok'],description:'Local E2E saved campaign'
  }}
 });
 expect(created.ok()).toBeTruthy();
 return {campaign:(await created.json()).campaign,token};
}
test('V3 Social Listening navigation shows campaigns, not retired Saved Searches or Review Queue',async({page})=>{
 await login(page);
 await page.goto('/social-listening');
 await expect(page.getByRole('heading',{name:'Social Listening'})).toBeVisible();
 await expect(page.getByRole('button',{name:/create campaign/i})).toBeVisible();
 await expect(page.getByRole('button',{name:/saved searches|review queue|discover sources/i})).toHaveCount(0);
});
test('V3 campaign captured posts and candidate watchlist stay in the selected campaign',async({page,request})=>{
 const {campaign}=await makeCampaign(request,'QA Campaign tabs '+Date.now());
 await login(page);
 await page.goto('/social-listening/campaigns/'+campaign.id);
 const sections=page.getByRole('navigation',{name:'Selected campaign sections'});
 await expect(sections.getByRole('button',{name:'Overview'})).toBeVisible();
 await sections.getByRole('button',{name:'Captured Posts'}).click();
 await expect(page.getByRole('region',{name:'Captured posts'})).toBeVisible();
 await sections.getByRole('button',{name:'Candidate Watchlist'}).click();
 await expect(page.locator('iframe[src*="watchlist-v2_2.html"]')).toHaveCount(1);
});
test('V3 separate Discover is explicit and cannot silently execute on navigation',async({page,request})=>{
 await makeCampaign(request,'QA Discover guard '+Date.now());
 const paid=[];page.on('request',r=>{if(/socialcrawl\.dev|api\.openai\.com/.test(r.url()))paid.push(r.url())});
 await login(page);
 await page.goto('/social-listening');
 await expect(page.getByRole('button',{name:/discover · 50 posts/i}).first()).toBeVisible();
 expect(paid).toEqual([]);
});
