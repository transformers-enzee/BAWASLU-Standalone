import { test, expect } from '@playwright/test';
import config from '../playwright.config.js';

const ADMIN_EMAIL='admin@bawaslu.local';
const ADMIN_PASSWORD=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
const ANALYST_EMAIL='qa.admin.analyst@example.com';
const ANALYST_PASSWORD='qa-admin-analyst-local';
const PROV_ADMIN_EMAIL='qa.prov.admin@example.com';
const PROV_ADMIN_PASSWORD='qa-prov-admin-local';

async function loginToken(request,email,password){
  const r=await request.post('/api/auth/login',{data:{email,password}});
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token;
}
async function registry(request,token,action,data={},id=null){
  return request.post('/api/functions/registry',{
    headers:{Authorization:'Bearer '+token},
    data:{action,data,id}
  });
}
async function ensureUser(request,email,password,name){
  const r=await request.post('/api/auth/register',{data:{email,password,full_name:name}});
  expect([200,409]).toContain(r.status());
}
async function users(request,token){
  const r=await registry(request,token,'users');
  expect(r.ok()).toBeTruthy();
  return (await r.json()).users;
}
function analystPermissions(){
  return {
    view_intelligence:true,add_intelligence:true,edit_intelligence:true,
    review_ai_suggestions:true,human_validation:false,verify_evidence:false,
    manage_watchlist:false,upload_evidence:true,manage_users:false,administration:false
  };
}
function provincialAdminPermissions(){
  return {
    view_intelligence:true,add_intelligence:true,edit_intelligence:true,
    review_ai_suggestions:true,human_validation:true,verify_evidence:false,
    manage_watchlist:true,upload_evidence:true,manage_users:true,administration:true
  };
}

test.describe.serial('Administration governance',()=>{
  let adminToken,analystId,provAdminId;

  test.beforeEach(async({request})=>{
    await ensureUser(request,ANALYST_EMAIL,ANALYST_PASSWORD,'QA Administration Analyst');
    await ensureUser(request,PROV_ADMIN_EMAIL,PROV_ADMIN_PASSWORD,'QA Provincial Administrator');
    adminToken=await loginToken(request,ADMIN_EMAIL,ADMIN_PASSWORD);
    const list=await users(request,adminToken);
    analystId=list.find(x=>x.email===ANALYST_EMAIL).id;
    provAdminId=list.find(x=>x.email===PROV_ADMIN_EMAIL).id;

    let r=await registry(request,adminToken,'setUser',{
      access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:analystPermissions(),status:'Active'
    },analystId);
    expect(r.ok()).toBeTruthy();

    r=await registry(request,adminToken,'setUser',{
      access_role:'Provincial Administrator',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:provincialAdminPermissions(),status:'Active'
    },provAdminId);
    expect(r.ok()).toBeTruthy();
  });

  test('national administrator can change role and restore it',async({request})=>{
    let r=await registry(request,adminToken,'setUser',{
      access_role:'Regency/City Analyst',geographic_scope:'Regency/City',province:'Bali',regency_city:'Kabupaten Bangli',
      permissions:analystPermissions(),status:'Active'
    },analystId);
    expect(r.ok()).toBeTruthy();
    let body=await r.json();
    expect(body.user.access_role).toBe('Regency/City Analyst');
    expect(body.user.geographic_scope).toBe('Regency/City');
    expect(body.user.regency_city).toBe('Kabupaten Bangli');

    r=await registry(request,adminToken,'setUser',{
      access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:analystPermissions(),status:'Active'
    },analystId);
    expect(r.ok()).toBeTruthy();
    body=await r.json();
    expect(body.user.access_role).toBe('Provincial Analyst');
    expect(body.user.geographic_scope).toBe('Province');
  });

  test('inactive assignment blocks protected registry actions until reactivated',async({request})=>{
    let r=await registry(request,adminToken,'setUser',{
      access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:analystPermissions(),status:'Inactive'
    },analystId);
    expect(r.ok()).toBeTruthy();

    const analystToken=await loginToken(request,ANALYST_EMAIL,ANALYST_PASSWORD);
    r=await registry(request,analystToken,'list');
    expect(r.status()).toBe(403);

    r=await registry(request,adminToken,'setUser',{
      access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:analystPermissions(),status:'Active'
    },analystId);
    expect(r.ok()).toBeTruthy();

    r=await registry(request,analystToken,'list');
    expect(r.ok()).toBeTruthy();
  });

  test('provincial administrator cannot assign national roles or nationwide scope',async({request})=>{
    const token=await loginToken(request,PROV_ADMIN_EMAIL,PROV_ADMIN_PASSWORD);

    let r=await registry(request,token,'setUser',{
      access_role:'National Analyst',geographic_scope:'Nationwide',province:'',regency_city:'',
      permissions:analystPermissions(),status:'Active'
    },analystId);
    expect(r.status()).toBe(403);

    r=await registry(request,token,'setUser',{
      access_role:'Viewer',geographic_scope:'Nationwide',province:'',regency_city:'',
      permissions:{view_intelligence:true},status:'Active'
    },analystId);
    expect(r.status()).toBe(403);
  });

  test('provincial administrator cannot delegate a permission they do not hold',async({request})=>{
    const token=await loginToken(request,PROV_ADMIN_EMAIL,PROV_ADMIN_PASSWORD);
    const elevated={...analystPermissions(),verify_evidence:true};
    const r=await registry(request,token,'setUser',{
      access_role:'Provincial Analyst',geographic_scope:'Province',province:'Bali',regency_city:'',
      permissions:elevated,status:'Active'
    },analystId);
    expect(r.status()).toBe(403);
  });

  test('access history records assignment changes',async({request})=>{
    const r=await registry(request,adminToken,'accessHistory',{},analystId);
    expect(r.ok()).toBeTruthy();
    const body=await r.json();
    expect(body.events.length).toBeGreaterThan(0);
    expect(body.events.some(x=>x.action==='USER_ACCESS_UPDATED')).toBeTruthy();
    const latest=body.events.find(x=>x.action==='USER_ACCESS_UPDATED');
    expect(latest.changes?.assignment?.new?.province).toBe('Bali');
  });
});
