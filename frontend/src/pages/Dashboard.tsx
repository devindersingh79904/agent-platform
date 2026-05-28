import { useEffect, useState } from 'react';
import { getAgents, getWorkflows, getRuns, getConfig } from '../api/client';
import { Link } from 'react-router-dom';
import { Users, GitBranch, PlayCircle, PlusCircle, LayoutGrid, Cpu, Search, Send } from 'lucide-react';
import { APP_ROUTES } from '../constants/appRoutes';
import { UI_MESSAGES } from '../constants/messages';
import { WORKFLOW_RUN_STATUS } from '../constants/workflow';

const Dashboard = () => {
  const [stats, setStats] = useState({ agents: 0, workflows: 0, runs: 0 });
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = () => {
    setLoading(true);
    setError(null);
    Promise.all([getAgents(), getWorkflows(), getRuns(), getConfig()]).then(([agents, workflows, runs, cfg]) => {
      setStats({
        agents: agents.length,
        workflows: workflows.length,
        runs: runs.length
      });
      setRecentRuns(runs.slice(0, 5));
      setConfig(cfg);
    }).catch(err => {
      console.error(UI_MESSAGES.DASHBOARD_FETCH_FAILED, err);
      setError(UI_MESSAGES.DASHBOARD_FETCH_FAILED);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <div className="flex space-x-3">
          <Link to={APP_ROUTES.TEMPLATES} className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-sm transition">
            <PlusCircle size={16} />
            <span>Create Workflow</span>
          </Link>
        </div>
      </div>
      {loading && <div className="bg-white border border-slate-200 rounded-lg p-6 text-slate-500">Loading dashboard...</div>}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={loadDashboard} className="underline">Retry</button>
        </div>
      )}
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Total Agents</div>
            <div className="text-4xl font-bold mt-2 text-slate-900">{stats.agents}</div>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg text-blue-600">
            <Users size={24} />
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Total Workflows</div>
            <div className="text-4xl font-bold mt-2 text-slate-900">{stats.workflows}</div>
          </div>
          <div className="bg-purple-50 p-3 rounded-lg text-purple-600">
            <GitBranch size={24} />
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Total Runs</div>
            <div className="text-4xl font-bold mt-2 text-slate-900">{stats.runs}</div>
          </div>
          <div className="bg-emerald-50 p-3 rounded-lg text-emerald-600">
            <PlayCircle size={24} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">LLM Mode</div>
            <div className="text-xl font-bold mt-1 text-slate-900">{config?.llm_mode === 'openai' ? 'OpenAI' : 'MockLLM'}</div>
            <div className="text-xs text-slate-500 font-mono mt-1">{config?.model || 'gpt-4o-mini'}</div>
          </div>
          <div className="bg-sky-50 p-3 rounded-lg text-sky-600">
            <Cpu size={22} />
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Search Provider</div>
            <div className="text-xl font-bold mt-1 text-slate-900">{config?.search_provider || 'duckduckgo'}</div>
            <div className="text-xs text-slate-500 mt-1">Real tool execution</div>
          </div>
          <div className="bg-amber-50 p-3 rounded-lg text-amber-600">
            <Search size={22} />
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider">Telegram</div>
            <div className="text-xl font-bold mt-1 text-slate-900">{config?.telegram_configured ? 'Enabled' : 'Disabled'}</div>
            <div className="text-xs text-slate-500 mt-1">{config?.database || 'sqlite'} database</div>
          </div>
          <div className="bg-emerald-50 p-3 rounded-lg text-emerald-600">
            <Send size={22} />
          </div>
        </div>
      </div>

      {/* Grid of details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Runs */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2">
          <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center space-x-2">
            <PlayCircle size={20} className="text-indigo-500" />
            <span>Recent Runs</span>
          </h2>
          {recentRuns.length === 0 ? (
            <div className="text-slate-500 py-8 text-center bg-slate-50 rounded-lg border border-dashed border-slate-200">
              No recent runs initiated yet.
            </div>
          ) : (
            <div className="space-y-3">
              {recentRuns.map(run => (
                <Link key={run.id} to={APP_ROUTES.RUN_MONITOR(run.id)} className="flex justify-between items-center p-4 hover:bg-slate-50 rounded-xl border border-slate-100 transition block">
                  <div className="font-mono text-sm text-indigo-600 font-medium">
                    Run ID: {run.id.substring(0, 8)}...
                  </div>
                  <div className="text-sm text-slate-500">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : "Pending"}
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                    run.status === WORKFLOW_RUN_STATUS.COMPLETED ? 'bg-green-50 text-green-700 border border-green-200' : 
                    run.status === WORKFLOW_RUN_STATUS.FAILED ? 'bg-red-50 text-red-700 border border-red-200' :
                    'bg-yellow-50 text-yellow-700 border border-yellow-200'
                  }`}>
                    {run.status}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center space-x-2">
            <LayoutGrid size={20} className="text-indigo-500" />
            <span>Quick Links</span>
          </h2>
          <div className="flex flex-col space-y-3">
            <Link to={APP_ROUTES.AGENTS} className="flex items-center space-x-3 p-3 hover:bg-slate-50 rounded-lg border border-slate-100 text-slate-700 hover:text-indigo-600 font-medium transition">
              <Users size={18} className="text-slate-400" />
              <span>Manage Agents</span>
            </Link>
            <Link to={APP_ROUTES.TEMPLATES} className="flex items-center space-x-3 p-3 hover:bg-slate-50 rounded-lg border border-slate-100 text-slate-700 hover:text-indigo-600 font-medium transition">
              <GitBranch size={18} className="text-slate-400" />
              <span>Create Workflows from Templates</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
