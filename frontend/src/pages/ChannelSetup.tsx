import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getConfig } from '../api/client';
import { MessageSquare, CheckCircle, AlertCircle, ArrowRight, Bot, Settings, Info } from 'lucide-react';
import { APP_ROUTES } from '../constants/appRoutes';

const ChannelSetup = () => {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch(err => {
        console.error("Failed to fetch config", err);
        setError("Failed to load channel configurations.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-500">Loading channel configuration...</div>;

  const isTelegramConfigured = config?.telegram_configured || false;
  const isDefaultWorkflowConfigured = config?.default_telegram_workflow_id_configured || false;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center space-x-3">
          <Bot className="text-indigo-600" size={32} />
          <span>Conversational Channels</span>
        </h1>
        <Link 
          to={APP_ROUTES.CHANNEL_MESSAGES} 
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold shadow-sm transition-colors text-sm"
        >
          <MessageSquare size={18} />
          <span>View Message Logs</span>
          <ArrowRight size={16} />
        </Link>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Telegram Channel Status Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
                <span>Telegram Bot Integration</span>
              </h2>
              <p className="text-slate-500 text-sm">Deploy your agents as a conversational Telegram bot.</p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${isTelegramConfigured && isDefaultWorkflowConfigured ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
              {isTelegramConfigured && isDefaultWorkflowConfigured ? 'Active' : 'Configuration Required'}
            </span>
          </div>

          <div className="border-t border-slate-100 pt-4 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">TELEGRAM_BOT_TOKEN</span>
              <div className="flex items-center space-x-1.5 font-semibold">
                {isTelegramConfigured ? (
                  <>
                    <CheckCircle className="text-emerald-500" size={16} />
                    <span className="text-emerald-700">Configured (Hidden)</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="text-amber-500" size={16} />
                    <span className="text-amber-700">Missing</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">DEFAULT_TELEGRAM_WORKFLOW_ID</span>
              <div className="flex items-center space-x-1.5 font-semibold">
                {isDefaultWorkflowConfigured ? (
                  <>
                    <CheckCircle className="text-emerald-500" size={16} />
                    <span className="text-emerald-700">Configured</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="text-amber-500" size={16} />
                    <span className="text-amber-700">Missing</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Worker Connection Mode</span>
              <span className="font-mono text-slate-700 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-xs">
                Polling (Long Poll)
              </span>
            </div>
          </div>
        </div>

        {/* Web UI Channel Status Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-slate-900">Web UI Channel</h2>
              <p className="text-slate-500 text-sm">Interact with workflows directly through the visual dashboard.</p>
            </div>
            <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold">
              Active
            </span>
          </div>

          <div className="border-t border-slate-100 pt-4 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Web UI Connector</span>
              <div className="flex items-center space-x-1.5 font-semibold">
                <CheckCircle className="text-emerald-500" size={16} />
                <span className="text-emerald-700">Ready</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Websocket Endpoint</span>
              <span className="font-mono text-slate-700 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-xs">
                Active (/ws)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Guide Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
          <Settings className="text-slate-500" size={22} />
          <span>Telegram Setup Instructions</span>
        </h2>

        <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
          <p>Follow these steps to configure your Telegram bot and connect it to a workflow run execution:</p>
          <ol className="list-decimal list-inside space-y-2">
            <li>
              Open Telegram and search for <strong className="text-slate-800">@BotFather</strong>. Send the command <code className="bg-slate-100 text-slate-700 px-1 py-0.5 rounded font-mono text-xs">/newbot</code> and follow instructions to get a token.
            </li>
            <li>
              Add the bot token to your local <code className="bg-slate-100 text-slate-700 px-1 py-0.5 rounded font-mono text-xs">.env</code> file under the variable:
              <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-xs my-2 overflow-x-auto">
                TELEGRAM_BOT_TOKEN=your_bot_token_here
              </pre>
            </li>
            <li>
              Configure the default workflow ID to trigger when messages are sent to the bot:
              <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-xs my-2 overflow-x-auto">
                DEFAULT_TELEGRAM_WORKFLOW_ID=wf_research_review
              </pre>
            </li>
            <li>
              Start the background bot listener worker using:
              <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-xs my-2 overflow-x-auto">
                make telegram
              </pre>
            </li>
            <li>
              Open Telegram and send a message to your bot. The bot will automatically trigger a workflow run in the background, update the message log, and respond to you once completed.
            </li>
          </ol>
        </div>

        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 flex items-start space-x-3 text-indigo-900 text-xs">
          <Info size={16} className="text-indigo-600 shrink-0 mt-0.5" />
          <p>
            For security, bot credentials are never exposed through metadata or API endpoints. All bot processing and workflow triggers occur completely on your server.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChannelSetup;
