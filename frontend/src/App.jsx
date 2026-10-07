import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import UserNotRegisteredError from '@/components/UserNotRegisteredError';
import ScrollToTop from './components/ScrollToTop';
import { Navigate } from 'react-router-dom';
import ProtectedRoute from '@/components/ProtectedRoute';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';
import Shell from '@/components/intel/Shell';
import AccessGate from '@/components/intel/AccessGate';
import Home from '@/pages/Home';
import Watchlist from '@/pages/Watchlist';
import WatchlistProfile from '@/pages/WatchlistProfile';
import Inbox from '@/pages/Inbox';
import IntelligenceAssistant from '@/pages/IntelligenceAssistant';
import AddIntelligence from '@/pages/AddIntelligence';
import IntelligenceDetail from '@/pages/IntelligenceDetail';
import DataSources from '@/pages/DataSources';
import SocialListening from '@/pages/SocialListening';
import Validation from '@/pages/Validation';
import Administration from '@/pages/Administration';

const AuthenticatedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError } = useAuth();

  // Show loading spinner while checking app public settings or auth
  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Handle authentication errors
  if (authError) {
    if (authError.type === 'user_not_registered') {
      return <UserNotRegisteredError />;
    }
  }

  // Render the main app
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedRoute unauthenticatedElement={<Navigate to={`/login?returnTo=${encodeURIComponent(window.location.pathname + window.location.search + window.location.hash)}`} replace />} />}>
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/watchlist/:id" element={<WatchlistProfile />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route element={<AccessGate permission="view_intelligence" />}>
            <Route path="/assistant" element={<IntelligenceAssistant />} />
          </Route>
          <Route path="/add" element={<AddIntelligence />} />
          <Route path="/intelligence/:id" element={<IntelligenceDetail />} />
          <Route path="/sources" element={<DataSources />} />
          <Route element={<AccessGate permission="view_intelligence" />}>
            <Route path="/social-listening" element={<SocialListening />} />
          </Route>
          <Route element={<AccessGate permission="human_validation" />}>
            <Route path="/validation" element={<Validation />} />
          </Route>
          <Route element={<AccessGate permission="administration" />}>
            <Route path="/administration" element={<Administration />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
};


function App() {

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <ScrollToTop />
          <AuthenticatedApp />
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App