import React from 'react'
import ReactDOM from 'react-dom/client'
import '@/index.css'

const demo=/^\/demo(?:\/|$)/.test(window.location.pathname);
if(demo){
  // A simple training-only gate. The demo bundle contains anonymized, fixed
  // evidence, so this is NOT server authentication or access control for secrets.
  const root=ReactDOM.createRoot(document.getElementById('root'));
  const openDemo=()=>{
    import('@/demo/realBridge.js').then(()=>{
      const csp=document.createElement('meta');
      csp.httpEquiv='Content-Security-Policy';
      csp.content="default-src 'self'; connect-src 'self'; form-action 'none'; object-src 'none'; frame-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'";
      document.head.appendChild(csp);
      return import('@/App.jsx');
    }).then(({default:App})=>root.render(<App/>));
  };
  // The demo contains only fixed, sanitized, read-only training evidence.
  // Open immediately: real application auth and admin routes remain protected.
  openDemo();
}else{
  import('@/App.jsx').then(({default:App})=>ReactDOM.createRoot(document.getElementById('root')).render(<App/>));
}
