export default function AccessPermissions({labels,permissions,onChange}){
 return <fieldset className="border-t border-border pt-4"><legend className="font-semibold text-sm pt-4">Functional permissions</legend>
  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">{Object.entries(labels).map(([key,label])=><label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-primary" checked={!!permissions?.[key]} onChange={e=>onChange(key,e.target.checked)}/>{label}</label>)}</div>
  <p className="text-xs text-muted-foreground mt-3">Human Validation, Verify Evidence and Manage Users &amp; Access require explicit approval.</p>
 </fieldset>;
}