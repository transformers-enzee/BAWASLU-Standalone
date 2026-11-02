import useTranslatedPresentationText from '@/lib/useTranslatedPresentationText';
/** Only use for derived AI interpretation. Original quotes and review inputs stay unchanged. */
export default function TranslatedIntelligenceText({text}){
 const {display,status}=useTranslatedPresentationText(text);
 return <span data-i18n-exempt className="whitespace-pre-wrap">{status&&<span role="status" className="text-xs text-slate-500">{status} </span>}{display}</span>;
}
