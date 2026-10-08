import { Link } from 'react-router-dom';
import Status from './Status';

const SOCIAL_PLATFORMS=new Set(['TikTok','Instagram','YouTube','Facebook','X','Threads','Reddit','LinkedIn']);
const sourceLabel=x=>SOCIAL_PLATFORMS.has(x.platform)&&x.observed_publisher_handle?x.observed_publisher_handle:(x.source_name||x.source_type||'—');
const locationLabel=x=>x.jurisdiction_confirmed!==true?'Jurisdiction unresolved':x.jurisdiction_type==='National'?'National':(x.geographic_assignments||[]).map(a=>[a.regency_city,a.province].filter(Boolean).join(', ')).filter(Boolean).join(' · ')||'Confirmed';

export default function IntelligenceTable({items=[]}){
  return <div className="intel-card overflow-hidden">
    <div className="overflow-x-auto">
      <table className="intel-table min-w-[920px]">
        <thead><tr>{['Intelligence','Source / Entity','Location','Evidence','Priority','Review status','Updated'].map(x=><th key={x}>{x}</th>)}</tr></thead>
        <tbody>{items.map(x=><tr key={x.id}>
          <td className="min-w-[260px] max-w-[340px]">
            <Link className="text-[#146a8b] text-xs font-semibold hover:underline" to={'/intelligence/'+x.id}>{x.intelligence_id}</Link>
            <Link className="block mt-1 font-semibold text-[#1e354b] hover:underline line-clamp-2" to={'/intelligence/'+x.id}>{x.title||'Untitled intelligence'}</Link>
            <div className="mt-1 text-[11px] text-[#8192a2]">{x.assigned_reviewer?'Reviewer: '+x.assigned_reviewer:'Unassigned'}</div>
          </td>
          <td className="min-w-[180px] max-w-[240px]">
            <div className="font-medium text-[#344c60]">{sourceLabel(x)}</div>
            <div className="text-xs text-[#8192a2]">{x.platform||x.source_type||'Source type not recorded'}</div>
            <div className="mt-1 text-xs text-[#617789] line-clamp-2">{x.related_entities?.join(', ')||'No related entity'}</div>
          </td>
          <td className="min-w-[170px] max-w-[230px] text-sm">{locationLabel(x)}</td>
          <td className="min-w-[150px]"><div className="flex flex-col gap-1.5 items-start"><Status value={x.evidence_type||(['OBSERVED','INFERRED'].includes(x.evidence_state)?x.evidence_state:'Not classified')}/><Status value={x.verification_status||(x.evidence_state==='VERIFIED'?'HUMAN_VERIFIED':'UNVERIFIED')}/></div></td>
          <td><Status value={x.priority}/></td>
          <td className="min-w-[190px]">
            <Status value={x.review_status}/>
            {(x.geographic_mismatch_review?.status||x.geographic_mismatch?.status)==='pending'&&<p className="mt-1 text-xs font-semibold text-destructive">GEOGRAPHIC MISMATCH — REVIEW REQUIRED</p>}
          </td>
          <td className="whitespace-nowrap text-sm">{new Date(x.updated_date||x.created_date).toLocaleDateString('en-GB')}</td>
        </tr>)}</tbody>
      </table>
    </div>
    {!items.length&&<div className="p-10 text-center text-sm text-[#73869a]">No intelligence matches the current view and filters.</div>}
  </div>;
}
