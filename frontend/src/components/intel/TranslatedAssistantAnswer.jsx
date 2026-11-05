import AssistantAnswer from './AssistantAnswer';
import useTranslatedPresentationText from '@/lib/useTranslatedPresentationText';
export default function TranslatedAssistantAnswer({text}){
 const clean=String(text||'').replaceAll('UNVERIFIED_SOCIAL_SOURCE','sumber belum diverifikasi').replaceAll('AI_RELEVANCE_NOT_LEGAL_VERIFICATION','relevansi AI belum menjadi kesimpulan hukum').replaceAll('AIR_RELEVANCE_NOT_LEGAL_VERIFICATION','relevansi AI belum menjadi kesimpulan hukum');
 const {display,status}=useTranslatedPresentationText(clean);
 return <div>{status&&<p role="status" className="mb-2 text-xs text-[#60768c]">{status}</p>}<AssistantAnswer text={display}/></div>;
}
