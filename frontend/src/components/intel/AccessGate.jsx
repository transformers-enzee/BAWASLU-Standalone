import { Outlet, useOutletContext } from 'react-router-dom';
export default function AccessGate({permission}){
 const {access}=useOutletContext();
 if(access.status!=='Active'||access.permissions?.[permission]!==true)return <div role="alert" className="intel-card p-6 text-sm">Access denied. Your BAWASLU assignment does not permit this page.</div>;
 return <Outlet context={{access}}/>;
}