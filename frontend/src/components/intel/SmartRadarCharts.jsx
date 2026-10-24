import { useMemo } from 'react';
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';
import { radarText } from '@/lib/smartRadarI18n';

const fmtDay = (day, language='en') => {
  const d = new Date(day + 'T00:00:00Z');
  return Number.isNaN(d.getTime()) ? day : d.toLocaleDateString(language==='id'?'id-ID':'en-US', { timeZone: 'UTC', day: 'numeric', month: 'short' });
};
function activitySeries(byDay) {
  const entries = Object.entries(byDay || {}).filter(([date,count]) => /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(count) && count >= 0).sort((a,b) => a[0].localeCompare(b[0]));
  if (!entries.length) return [];
  const start = new Date(entries[0][0] + 'T00:00:00Z').getTime();
  const end = new Date(entries[entries.length-1][0] + 'T00:00:00Z').getTime();
  const duration = Math.min(180, Math.round((end-start)/86400000)+1);
  const first = end-(duration-1)*86400000;
  const counts = Object.fromEntries(entries);
  const rows = [];
  for(let i=0;i<duration;i++) {
    const date = new Date(first+i*86400000).toISOString().slice(0,10);
    const posts = counts[date] || 0;
    rows.push({ date, label:fmtDay(date), posts });
  }
  for(let i=0;i<rows.length;i++) {
    const slice=rows.slice(Math.max(0,i-6),i+1);
    rows[i].average=Number((slice.reduce((acc,r)=>acc+r.posts,0)/slice.length).toFixed(1));
  }
  return rows;
}
const COLORS = {facebook:'#1877b6',instagram:'#b65c87',x:'#293d54',twitter:'#293d54',tiktok:'#22a69c',youtube:'#d95c5c',threads:'#736aa2'};
const OTHER = ['#d2a753','#3875a3','#8c72aa','#619567'];

export function SourceActivityChart({byDay,language='en'}) {
  const tr=key=>radarText(language,key);
  const data=useMemo(()=>activitySeries(byDay),[byDay]);
  if(!data.length) return <p className="text-sm text-slate-500 py-16 text-center">{tr('No dated source posts for the selected filters.')}</p>;
  return <div className="w-full">
    <div className="h-[270px] w-full" role="img" aria-label={tr('Daily published supporting posts and seven-day moving average line chart')}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{top:15,right:13,left:-15,bottom:0}}>
          <CartesianGrid strokeDasharray="3 4" stroke="#e2e8f0" vertical={false}/>
          <XAxis dataKey="date" tickFormatter={day=>fmtDay(day,language)} tick={{fontSize:10,fill:'#64748b'}} minTickGap={28} axisLine={{stroke:'#e2e8f0'}} tickLine={false}/>
          <YAxis allowDecimals={false} domain={[0,'auto']} tick={{fontSize:11,fill:'#64748b'}} axisLine={false} tickLine={false}/>
          <Tooltip labelFormatter={v=>fmtDay(v,language)} contentStyle={{borderRadius:12,border:'1px solid #e2e8f0',fontSize:12}}/>
          <Legend verticalAlign="bottom" wrapperStyle={{fontSize:12,paddingTop:12}}/>
          <Line type="monotone" name={tr("Posts published")} dataKey="posts" stroke="#137f70" strokeWidth={2.7} dot={data.length<=16?{r:3}:false} activeDot={{r:5}} isAnimationActive={false}/>
          <Line type="monotone" name={tr("7-day average")} dataKey="average" stroke="#d19a43" strokeWidth={2.2} strokeDasharray="6 4" dot={false} isAnimationActive={false}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
    <p className="text-xs text-slate-500 mt-2">{tr('Published posts per calendar day, not new discoveries or confirmed incidents. The dashed line smooths daily changes.')}</p>
  </div>;
}

export function SourcePlatformsDonut({byPlatform,language='en'}) {
  const tr=key=>radarText(language,key);
  const data=useMemo(()=>Object.entries(byPlatform || {}).filter(([,n])=>Number(n)>0).sort((a,b)=>b[1]-a[1]).map(([name,value],index)=>({
    name, value:Number(value), color:COLORS[name.toLowerCase()]||OTHER[index%OTHER.length]
  })),[byPlatform]);
  const total=data.reduce((sum,x)=>sum+x.value,0);
  if(!total)return <p className="text-sm text-slate-500 py-16 text-center">{tr('No source-platform data for this selection.')}</p>;
  return <div className="grid sm:grid-cols-[1fr_1fr] gap-3 items-center">
    <div className="relative h-[240px] min-w-0" role="img" aria-label={tr('Donut chart showing the distribution of supporting posts by platform')}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="64%" outerRadius="91%" stroke="#fff" strokeWidth={2} paddingAngle={2} isAnimationActive={false}>
            {data.map(x=><Cell key={x.name} fill={x.color}/>)}
          </Pie>
          <Tooltip formatter={(value,name)=>[value+' '+tr('posts')+' ('+(value*100/total).toFixed(1)+'%)',name]} contentStyle={{borderRadius:12,fontSize:12}}/>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col justify-center items-center pointer-events-none">
        <b className="text-2xl text-slate-800">{total}</b><span className="text-[11px] text-slate-500">{tr('Posts')}</span>
      </div>
    </div>
    <div className="space-y-2" aria-label={tr('Source-platform donut chart legend')}>
      {data.map(item=><div key={item.name} className="flex items-center gap-2 text-xs">
        <span className="w-3 h-3 rounded-sm shrink-0" style={{backgroundColor:item.color}}/>
        <span className="flex-1 text-slate-700">{item.name}</span>
        <span className="tabular-nums text-slate-600">{(item.value*100/total).toFixed(1)}%</span>
        <b className="tabular-nums text-slate-800 w-7 text-right">{item.value}</b>
      </div>)}
    </div>
    <p className="text-xs text-slate-500 sm:col-span-2">{tr('Shares of supporting posts in the current perspective and filters; one post is counted once.')}</p>
  </div>;
}
