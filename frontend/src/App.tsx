import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import AgentsList from './pages/AgentsList';
import WorkflowBuilder from './pages/WorkflowBuilder';
import WorkflowsList from './pages/WorkflowsList';
import RunMonitor from './pages/RunMonitor';
import RunsList from './pages/RunsList';

import TemplatesGallery from './pages/TemplatesGallery';
import SchedulesManager from './pages/SchedulesManager';
import MemoryManager from './pages/MemoryManager';
import ChannelMessages from './pages/ChannelMessages';
import ChannelSetup from './pages/ChannelSetup';
import { APP_ROUTES } from './constants/appRoutes';
import { Menu } from 'lucide-react';

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close sidebar on route change by adjusting state in render
  const [prevPath, setPrevPath] = useState(location.pathname);
  if (location.pathname !== prevPath) {
    setPrevPath(location.pathname);
    setSidebarOpen(false);
  }

  // Disable body scroll when mobile sidebar is open
  useEffect(() => {
    if (sidebarOpen) {
      document.body.classList.add('overflow-hidden');
    } else {
      document.body.classList.remove('overflow-hidden');
    }
    return () => {
      document.body.classList.remove('overflow-hidden');
    };
  }, [sidebarOpen]);

  // Handle Escape key to close sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col lg:flex-row relative">
      {/* Mobile Topbar */}
      <header className="lg:hidden bg-slate-900 text-white flex items-center justify-between px-4 py-3 sticky top-0 z-30 shadow-md">
        <span className="font-bold text-lg truncate pr-4">
          {import.meta.env.VITE_APP_NAME || "Devinder AI Agent Studio"}
        </span>
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Open navigation"
          className="p-2 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
        >
          <Menu size={24} />
        </button>
      </header>

      {/* Sidebar Backdrop */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-45 transition-opacity"
        />
      )}

      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content */}
      <main className="flex-1 min-w-0 p-4 md:p-6 lg:p-8 lg:ml-64 min-h-[calc(100vh-56px)] lg:min-h-screen overflow-x-hidden">
        <Routes>
          <Route path={APP_ROUTES.DASHBOARD} element={<Dashboard />} />
          <Route path={`${APP_ROUTES.WORKFLOWS}/:workflowId`} element={<WorkflowBuilder />} />
          <Route path={APP_ROUTES.WORKFLOWS} element={<WorkflowsList />} />
          <Route path={APP_ROUTES.AGENTS} element={<AgentsList />} />
          <Route path={APP_ROUTES.TEMPLATES} element={<TemplatesGallery />} />
          <Route path={APP_ROUTES.RUNS} element={<RunsList />} />
          <Route path={`${APP_ROUTES.RUNS}/:runId`} element={<RunMonitor />} />
          <Route path={APP_ROUTES.SCHEDULES} element={<SchedulesManager />} />
          <Route path={APP_ROUTES.MEMORY} element={<MemoryManager />} />
          <Route path={APP_ROUTES.CHANNELS} element={<ChannelSetup />} />
          <Route path={APP_ROUTES.CHANNEL_MESSAGES} element={<ChannelMessages />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
