export function publicationLabel(item){
  if(item.publication_time_precision==='UNKNOWN')return 'Unknown';
  if(item.publication_date&&/^\d{4}-\d{2}-\d{2}$/.test(item.publication_date)){
    const [year,month,day]=item.publication_date.split('-').map(Number);
    const date=new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric'}).format(new Date(year,month-1,day));
    if(item.publication_time_precision==='TIME_UNKNOWN')return `${date} · Time unknown`;
    if(item.publication_time_precision==='EXACT')return `${date} · ${item.publication_datetime?.slice(11,16)||'Time unknown'}`;
  }
  return item.publication_datetime||'Not recorded';
}