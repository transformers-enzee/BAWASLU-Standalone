import React from 'react'
import ReactDOM from 'react-dom/client'
import '@/index.css'

// The public demo is a separate entry branch: it never imports AuthProvider,
// account clients, production services, live routes, or AI integrations.
const isDemo = /^\/demo(?:\/|$)/.test(window.location.pathname)
if (isDemo) {
  // Browser-enforced isolation: no fetch/XHR/WebSocket or external embeds.
  const demoCsp=document.createElement('meta')
  demoCsp.httpEquiv='Content-Security-Policy'
  demoCsp.content="default-src 'self'; connect-src 'none'; form-action 'none'; object-src 'none'; frame-src 'none'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'"
  document.head.appendChild(demoCsp)
  import('@/demo/DemoApp.jsx').then(({default:DemoApp})=>{
    ReactDOM.createRoot(document.getElementById('root')).render(<DemoApp />)
  })
} else {
  import('@/App.jsx').then(({default:App})=>{
    ReactDOM.createRoot(document.getElementById('root')).render(<App />)
  })
}
