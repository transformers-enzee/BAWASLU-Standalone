import AssistantAnswer from './AssistantAnswer';
import useTranslatedPresentationText from '@/lib/useTranslatedPresentationText';
export default function TranslatedAssistantAnswer({text}){
 const {display,status}=useTranslatedPresentationText(text);
 return <div>{status&&<p role="status" className="mb-2 text-xs text-[#60768c]">{status}</p>}<AssistantAnswer text={display}/></div>;
}
