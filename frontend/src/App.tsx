import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
import { APP_ROUTES } from './constants/appRoutes';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex">
        <Sidebar />
        <main className="flex-1 ml-64 p-8 overflow-y-auto h-screen">
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
            <Route path={APP_ROUTES.CHANNELS} element={<ChannelMessages />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
