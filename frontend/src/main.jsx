import React from 'react'
import ReactDOM from 'react-dom/client'
import '@/index.css'

const demo=/^\/demo(?:\/|$)/.test(window.location.pathname);
if(demo){
  // Import the API isolation adapter before importing the real application.
  import('@/demo/realBridge.js').then(()=>{
    const csp=document.createElement('meta');
    csp.httpEquiv='Content-Security-Policy';
    csp.content="default-src 'self'; connect-src 'self'; form-action 'none'; object-src 'none'; frame-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'";
    document.head.appendChild(csp);
    return import('@/App.jsx');
  }).then(({default:App})=>ReactDOM.createRoot(document.getElementById('root')).render(<App/>));
}else{
  import('@/App.jsx').then(({default:App})=>ReactDOM.createRoot(document.getElementById('root')).render(<App/>));
}
