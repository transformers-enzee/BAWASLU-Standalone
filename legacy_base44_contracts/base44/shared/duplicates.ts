const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim();
const tokens=s=>new Set(norm(s).split(' ').filter(w=>w.length>3));
const similarity=(a,b)=>{const x=tokens(a),y=tokens(b);return x.size>=3&&y.size>=3?[...x].filter(w=>y.has(w)).length/Math.max(x.size,y.size):0};
const canonical=s=>{try{const u=new URL(s);return (u.hostname.replace(/^www\./,'')+u.pathname.replace(/\/$/,'')).toLowerCase()}catch{return ''}};
export function findDuplicate(items,data){return items.map(x=>{
 let score=0;
 if(data.source_url&&x.source_url===data.source_url)score+=100;
 else if(data.source_url&&x.source_url&&canonical(x.source_url)===canonical(data.source_url))score+=70;
 else if(data.source_url&&x.source_url&&similarity(canonical(x.source_url),canonical(data.source_url))>.85)score+=45;
 if(similarity(x.title,data.title)>.75||norm(x.title)===norm(data.title)&&norm(data.title).length>12)score+=45;
 if(similarity(x.original_content,data.original_content)>.75)score+=35;
 if((x.related_entities||[]).some(v=>(data.related_entities||[]).includes(v)))score+=10;
 if((x.related_topics||[]).some(v=>(data.related_topics||[]).includes(v)))score+=10;
 const a=Date.parse(x.publication_datetime),b=Date.parse(data.publication_datetime);
 if(Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<48*3600000)score+=10;
 return {x,score};
 }).filter(v=>v.score>=55).sort((a,b)=>b.score-a.score)[0]?.x;
}