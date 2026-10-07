export function mergeRetrieved(form,result,languageTouched){
  const next={...form};
  for(const key of ['title','original_content','author','source_name'])if(!next[key]&&result[key])next[key]=result[key];
  if(result.platform)next.platform=result.platform;
  if(!languageTouched&&result.original_language_code)next.original_language_code=result.original_language_code;
  if(next.publication_time_precision==='UNKNOWN'&&result.publication_date){
    next.publication_date=result.publication_date;
    next.publication_time_precision=result.publication_time_precision;
    next.publication_time=result.publication_time||'';
  }
  return next;
}