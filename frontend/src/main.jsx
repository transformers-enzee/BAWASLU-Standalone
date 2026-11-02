import React from 'react'
import ReactDOM from 'react-dom/client'
import '@/index.css'

// The public demo is a separate entry branch: it never imports AuthProvider,
// Supabase clients, production services, live routes, or AI integrations.
const isDemo = /^\/demo(?:\/|$)/.test(window.location.pathname)
if (isDemo) {
  import('@/demo/DemoApp.jsx').then(({default:DemoApp})=>{
    ReactDOM.createRoot(document.getElementById('root')).render(<DemoApp />)
  })
} else {
  import('@/App.jsx').then(({default:App})=>{
    ReactDOM.createRoot(document.getElementById('root')).render(<App />)
  })
}
