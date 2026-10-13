export function publicationLabel(item){
  if(item.publication_time_precision==='UNKNOWN')return 'Unknown';
  if(item.publication_date&&/^\d{4}-\d{2}-\d{2}$/.test(item.publication_date)){
    const [year,month,day]=item.publication_date.split('-').map(Number);
    const date=new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric'}).format(new Date(year,month-1,day));
    if(item.publication_time_precision==='TIME_UNKNOWN')return `${date} · Time unknown`;
    if(item.publication_time_precision==='EXACT'){
      const time=item.publication_time||item.publication_datetime?.match(/[T ](\d{2}:\d{2})/)?.[1];
      return `${date} · ${time&&/^([01]\\d|2[0-3]):[0-5]\\d$/.test(time)?time:'Time unknown'}`;
    }
  }
  return item.publication_datetime||'Not recorded';
}