export function mergeRetrieved(form,result,languageTouched){
  const next={...form};
  for(const key of ['title','original_content','author','source_name'])if(!next[key]&&result[key])next[key]=result[key];
  if(result.platform)next.platform=result.platform;
  if(!languageTouched&&result.original_language_code)next.original_language_code=result.original_language_code;
  if(next.publication_time_precision==='UNKNOWN'&&result.publication_date){
    next.publication_date=result.publication_date;
    next.publication_time_precision=result.publication_time_precision==='DATE_ONLY'?'TIME_UNKNOWN':result.publication_time_precision;
    next.publication_time=result.publication_time||'';
  }
  const metadata={...(next.provider_source_metadata||{})};
  const retrieval={...(metadata.retrieval||{})};
  if(result.raw_original_content)retrieval.raw_original_content=result.raw_original_content;
  if(result.source_cleaning)retrieval.source_cleaning=result.source_cleaning;
  if(result.language_detection)retrieval.language_detection=result.language_detection;
  if(result.retrieval_status)retrieval.retrieval_status=result.retrieval_status;
  if(result.retrieved_url)retrieval.retrieved_url=result.retrieved_url;
  if(Object.keys(retrieval).length)metadata.retrieval=retrieval;
  if(!languageTouched&&result.original_language_code){
    metadata.language_selection_source='SYSTEM_DETECTED';
    metadata.language_selection_code=result.original_language_code;
  }
  next.provider_source_metadata=metadata;
  return next;
}
