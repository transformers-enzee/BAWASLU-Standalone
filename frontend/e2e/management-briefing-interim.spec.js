import {test, expect} from '@playwright/test';
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

const sample={
 period:'weekly',topic_filter:'',window_start_utc:'2026-11-01T00:00:00Z',
 window_end_utc:'2026-11-08T00:00:00Z',
 scope:{geographic_scope:'Province',province:'Riau'},
 metrics:{assignments:1,unique_linked_sources:1,active_assignments:1,
  closed_assignments:0,submitted_reports:0,approved_reports:0},
 case_status_counts:{OPEN:1},report_status_counts:{},
 department_counts:{'Penanganan Pelanggaran':1},verified_incident_province_counts:{Riau:1},
 recent_cases:[{id:9,title:'Riau source review',created_at:'2026-11-03T10:00:00',
  status:'OPEN',department:'Penanganan Pelanggaran',source_type:'SOCIAL',
  source_id:'15',source_url:'https://example.invalid/post/15'}],
 disclaimer:'Officer casework snapshot only; no legal verdict.',
 template:{
  template_version:'INTERIM-1.0',approval_state:'DRAFT_NOT_APPROVED',
  title:'Oversight Intelligence Management Brief',
  subtitle:'INTERNAL DRAFT · INTERIM TEMPLATE',period_label:'Weekly',scope_label:'Riau',
  topic:'',executive_summary:'One saved officer assignment requires source verification.',
  findings:[{case_id:9,title:'Riau source review',department:'Penanganan Pelanggaran',
   source_reference:'SOCIAL #15 / campaign #10',status:'OPEN',
   source_excerpt:'Alleged irregularity mentioned in an unverified post.',
   verification_note:'Casework status only; no legal verdict.',
   source_url:'https://example.invalid/post/15'}],
  recommended_actions:['Confirm original source before officer determination.'],
  methodology:['Not an official BAWASLU report; review and approval required.'],
  signoff:{prepared_by:'',reviewed_by:'',approved_by:'',date:''},
 }
};

test('Command Centre interim template renders source-backed preview and PDF download',async({page})=>{
 const paid=[];
 page.on('request',request=>{if(/api\.openai\.com|socialcrawl\.dev/.test(request.url()))paid.push(request.url())});
 await page.route('**/api/management-reporting/briefing?*',route=>
  route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(sample)}));
 await page.route('**/api/management-reporting/briefing.pdf?*',route=>
  route.fulfill({status:200,headers:{
   'Content-Type':'application/pdf',
   'Content-Disposition':'attachment; filename="bawaslu-interim-briefing-weekly.pdf"'
  },body:Buffer.from('%PDF-1.4 test fixture')}));
 await login(page);
 await page.goto('/smart-radar');
 await page.getByRole('button',{name:/Reports & Briefings|Laporan & Ringkasan/}).click();
 const template=page.getByTestId('interim-report-template');
 await expect(template).toBeVisible();
 await expect(template).toContainText('INTERIM-1.0');
 await expect(template).toContainText('DRAFT');
 await expect(page.getByText('Riau source review').first()).toBeVisible();
 await expect(page.getByText(/Source-linked assignments|Penugasan beserta sumber/)).toBeVisible();
 await expect(page.getByRole('button',{name:'Word (.docx)'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Excel (.xlsx)'})).toBeVisible();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'PDF',exact:true}).click();
 const download=await downloadPromise;
 expect(download.suggestedFilename()).toBe('bawaslu-interim-briefing-weekly.pdf');
 expect(paid).toEqual([]);
});
