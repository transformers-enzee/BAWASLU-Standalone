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
  closed_assignments:0,submitted_reports:0,approved_reports:0,
  assignments_with_reports:1,assignments_without_reports:0,report_versions_recorded:2},
 case_status_counts:{OPEN:1},report_status_counts:{},
 department_counts:{'Penanganan Pelanggaran':1},verified_incident_province_counts:{Riau:1},
 report_coverage:{assignments_in_period:1,assignments_with_reports:1,
   assignments_without_reports:0,stored_report_versions:2,
   preview_limit:12,preview_rows:1,template_limit:8,template_rows:1,
   preview_is_sample:false,template_is_sample:false},
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
 const coverage=page.getByTestId('briefing-data-coverage');
 await expect(coverage).toContainText(/Stored report versions|Versi laporan tersimpan/);
 await expect(coverage).toContainText(/latest saved report version per assignment|versi laporan terbaru per penugasan/i);
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


test('Optional Inbox monitoring is independent, sampled and export-consistent',async({page})=>{
 const requested=[];
 const monitoring={
  enabled:true,published_in_period:2,
  unique_relevant_sources_in_recent_inbox:3,
  publication_date_unknown:1,published_outside_period:0,
  flagged_potential_violation_posts:1,public_concern_posts:1,
  sentiment_counts:{NEGATIVE:1,NEUTRAL:1},
  platform_counts:{X:1,Reddit:1},
  inbox_window_limit:300,inbox_window_unit:'LINKS_PER_AUTHORIZED_CAMPAIGN',
  inbox_truncation_status:'UNKNOWN',legal_violations_confirmed:false,
  all_platform_conversations_counted:false
 };
 const withMonitoring={...sample,monitoring,
  template:{...sample.template,
   scorecard:[{label:'Observed Inbox posts (sample)',value:2}],
   methodology:[...sample.template.methodology,'Monitoring sample is not a census'],
   monitoring_summary:monitoring}};
 page.route('**/api/management-reporting/briefing?*',route=>{
  const url=route.request().url();
  requested.push(url);
  const data=new URL(url).searchParams.get('include_monitoring')==='true'
    ?withMonitoring:sample;
  return route.fulfill({status:200,contentType:'application/json',
    body:JSON.stringify(data)});
 });
 let exportUrl='';
 page.route('**/api/management-reporting/briefing.docx?*',route=>{
  exportUrl=route.request().url();
  return route.fulfill({status:200,headers:{
   'Content-Type':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
   'Content-Disposition':'attachment; filename="bawaslu-interim-briefing-weekly.docx"'
  },body:Buffer.from('PK synthetic fixture')});
 });
 await login(page);
 await page.goto('/smart-radar');
 await page.getByRole('button',{name:/Reports & Briefings|Laporan & Ringkasan/}).click();
 await expect(page.getByTestId('briefing-monitoring-option')).toBeVisible();
 await expect(page.getByTestId('briefing-intelligence-monitoring')).toHaveCount(0);
 await page.getByTestId('briefing-monitoring-option').locator('input').check();
 const panel=page.getByTestId('briefing-intelligence-monitoring');
 await expect(panel).toBeVisible();
 await expect(panel).toContainText(/Published in selected window|Dipublikasikan dalam periode/);
 await expect(panel).toContainText(/not an all-platform census|bukan sensus seluruh platform/i);
 await expect(panel).toContainText('300');
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Word (.docx)'}).click();
 await download;
 expect(exportUrl).toContain('include_monitoring=true');
 expect(requested.some(x=>x.includes('include_monitoring=false'))).toBeTruthy();
 expect(requested.some(x=>x.includes('include_monitoring=true'))).toBeTruthy();
});
