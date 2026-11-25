import {test as base, expect} from '@playwright/test';
import config from '../../playwright.config.js';
const email='admin@bawaslu.local';
const password=config.webServer?.[0]?.env?.BAWASLU_BOOTSTRAP_ADMIN_PASSWORD;
// Authenticate once per worker against the disposable local QA backend.
// Never reuse a live environment's browser session or write credentials to disk.
export const test=base.extend({
 localAdmin:[async({playwright},use)=>{
  const origin=config.use.baseURL;
  if(!config.webServer||!['127.0.0.1','localhost'].includes(new URL(origin).hostname))throw new Error('QA auth fixture requires isolated local backend');
  const api=await playwright.request.newContext({baseURL:origin});
  try{
   const auth=await api.post('/api/auth/login',{data:{email,password}});
   expect(auth.ok()).toBeTruthy();
   const token=(await auth.json()).access_token;
   expect(token).toBeTruthy();
   await use({origin,token});
  }finally{await api.dispose();}
 },{scope:'worker'}],
 storageState:async({localAdmin},use)=>{
  await use({cookies:[],origins:[{origin:localAdmin.origin,localStorage:[{name:'bawaslu_access_token',value:localAdmin.token}]}]});
 }
});

export {expect};
