import { Link } from 'react-router-dom';
import Status from './Status';

const SOCIAL_PLATFORMS=new Set(['TikTok','Instagram','YouTube','Facebook','X','Threads','Reddit','LinkedIn']);
const sourceLabel=x=>SOCIAL_PLATFORMS.has(x.platform)&&x.observed_publisher_handle?x.observed_publisher_handle:(x.source_name||x.source_type||'—');
const locationLabel=x=>x.jurisdiction_confirmed!==true?'Jurisdiction unresolved':x.jurisdiction_type==='National'?'National':(x.geographic_assignments||[]).map(a=>[a.regency_city,a.province].filter(Boolean).join(', ')).filter(Boolean).join(' · ')||'Confirmed';
const dateLabel=x=>{const d=new Date(x.updated_date||x.created_date);return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('en-GB')};

export default function IntelligenceTable({items=[]}){
  return <div className="space-y-3">
    {items.map(x=><article key={x.id} className="intel-card p-4 md:p-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(150px,.9fr)_minmax(150px,.9fr)_auto] xl:items-start">
        <div className="min-w-0">
          <Link className="text-[#146a8b] text-xs font-semibold hover:underline" to={'/intelligence/'+x.id}>{x.intelligence_id}</Link>
          <Link className="block mt-1 font-semibold text-[#1e354b] hover:underline line-clamp-2" to={'/intelligence/'+x.id}>{x.title||'Untitled intelligence'}</Link>
          <div className="mt-2 text-xs text-[#617789]">
            <span className="font-medium text-[#344c60]">{sourceLabel(x)}</span>
            <span className="text-[#8192a2]"> · {x.platform||x.source_type||'Source type not recorded'}</span>
          </div>
          <div className="mt-1 text-xs text-[#617789] line-clamp-2">{x.related_entities?.join(', ')||'No related entity'}</div>
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-[.12em] font-bold text-[#8a9aa9]">Location</p>
          <p className="mt-1 text-sm text-[#445b70]">{locationLabel(x)}</p>
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-[.12em] font-bold text-[#8a9aa9]">Evidence</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <Status value={x.evidence_type||(['OBSERVED','INFERRED'].includes(x.evidence_state)?x.evidence_state:'Not classified')}/>
            <Status value={x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED')}/>
          </div>
        </div>

        <div className="xl:text-right">
          <p className="text-[10px] uppercase tracking-[.12em] font-bold text-[#8a9aa9]">Priority</p>
          <div className="mt-1 xl:flex xl:justify-end"><Status value={x.priority}/></div>
        </div>
      </div>

      <div className="mt-4 border-t border-[#edf1f5] pt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Status value={x.review_status}/>
          {(x.geographic_mismatch_review?.status||x.geographic_mismatch?.status)==='pending'&&<span className="text-xs font-semibold text-destructive">Geographic mismatch review required</span>}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#8192a2]">
          <span>{x.assigned_reviewer?'Reviewer: '+x.assigned_reviewer:'Unassigned'}</span>
          <span>Updated: {dateLabel(x)}</span>
        </div>
      </div>
    </article>)}
    {!items.length&&<div className="intel-card p-10 text-center text-sm text-[#73869a]">No intelligence matches the current view and filters.</div>}
  </div>;
}
