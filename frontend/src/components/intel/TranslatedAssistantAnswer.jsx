import AssistantAnswer from './AssistantAnswer';
import useTranslatedPresentationText from '@/lib/useTranslatedPresentationText';
import {friendlySource} from '@/lib/assistantResponseLocale';
export default function TranslatedAssistantAnswer({text,language='',labels={}}){
 const clean=friendlySource(text,language||'id',labels);
 const {display,status}=useTranslatedPresentationText(clean,language);
 return <div lang={language||undefined}>{status&&<p role="status" className="mb-2 text-xs text-[#60768c]">{status}</p>}<AssistantAnswer text={display}/></div>;
}
