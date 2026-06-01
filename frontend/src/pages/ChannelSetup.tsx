import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getChannels } from '../api/client';
import type { ChannelStatusResponse } from '../api/client';
import { MessageSquare, CheckCircle, AlertCircle, ArrowRight, Bot, Settings, Info, Copy, ExternalLink, QrCode } from 'lucide-react';
import { APP_ROUTES } from '../constants/appRoutes';
import { QRCodeSVG } from 'qrcode.react';

const ChannelSetup = () => {
  const [config, setConfig] = useState<ChannelStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');

  useEffect(() => {
    getChannels()
      .then(setConfig)
      .catch(err => {
        console.error("Failed to fetch config", err);
        setError("Failed to load channel configurations.");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleCopyLink = async () => {
    if (!config?.telegram?.bot_url) return;
    try {
      await navigator.clipboard.writeText(config.telegram.bot_url);
      setCopyStatus('copied');
      setTimeout(() => setCopyStatus('idle'), 2000);
    } catch (err) {
      setCopyStatus('error');
      setTimeout(() => setCopyStatus('idle'), 3000);
    }
  };

  if (loading) return <div className="text-slate-500">Loading channel configuration...</div>;

  const telegram = config?.telegram;
  const isTelegramConfigured = telegram?.bot_token_configured || false;
  const isDefaultWorkflowConfigured = telegram?.default_workflow_configured || false;
  const isTelegramActive = telegram?.active || false;
  const botUrl = telegram?.bot_url;
  const botUsername = telegram?.bot_username;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center space-x-3">
          <Bot className="text-indigo-600" size={32} />
          <span>Conversational Channels</span>
        </h1>
        <Link 
          to={APP_ROUTES.CHANNEL_MESSAGES} 
          className="flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold shadow-sm transition-colors text-sm w-full sm:w-auto"
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
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${isTelegramActive ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
              {isTelegramActive ? 'Active' : 'Configuration Required'}
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
              <span className="text-slate-600">Telegram Bot</span>
              <div className="flex items-center space-x-1.5 font-semibold">
                {botUsername ? (
                  <span className="text-indigo-600">@{botUsername}</span>
                ) : (
                  <span className="text-slate-400">Not configured</span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Worker Connection Mode</span>
              <span className="font-mono text-slate-700 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded text-xs">
                {telegram?.connection_mode || "Polling (Long Poll)"}
              </span>
            </div>
            
            {/* Action Buttons & QR Code */}
            <div className="border-t border-slate-100 pt-4 mt-2">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                <div className="flex flex-col space-y-2 w-full sm:w-auto">
                  <a 
                    href={botUrl || "#"} 
                    target="_blank" 
                    rel="noreferrer"
                    className={`flex items-center justify-center space-x-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors ${botUrl ? 'bg-[#24A1DE] hover:bg-[#1f8cbd] text-white' : 'bg-slate-100 text-slate-400 cursor-not-allowed'}`}
                    onClick={(e) => !botUrl && e.preventDefault()}
                  >
                    <ExternalLink size={16} />
                    <span>Open Telegram Bot</span>
                  </a>
                  <button 
                    onClick={handleCopyLink}
                    disabled={!botUrl}
                    className={`flex items-center justify-center space-x-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors border ${botUrl ? 'border-slate-200 hover:bg-slate-50 text-slate-700' : 'border-slate-100 text-slate-300 cursor-not-allowed'}`}
                  >
                    <Copy size={16} />
                    <span>Copy Bot Link</span>
                  </button>
                  {copyStatus === 'copied' && <span className="text-xs text-emerald-600 font-medium text-center">Copied!</span>}
                  {copyStatus === 'error' && <span className="text-xs text-rose-500 font-medium text-center">Unable to copy. Please copy manually.</span>}
                  {!botUrl && <span className="text-xs text-slate-500 text-center">Bot username is not configured.</span>}
                </div>

                {botUrl && (
                  <div className="flex flex-col items-center space-y-2 bg-slate-50 p-3 rounded-lg border border-slate-100 self-center">
                    <QRCodeSVG value={botUrl} size={80} className="bg-white p-1 rounded" />
                    <span className="text-xs font-medium text-slate-500 flex items-center space-x-1">
                      <QrCode size={12} />
                      <span>Scan to open</span>
                    </span>
                  </div>
                )}
              </div>
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
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${config?.web_ui?.active ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
              {config?.web_ui?.active ? 'Active' : 'Inactive'}
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
                Active ({config?.web_ui?.websocket_endpoint || '/ws'})
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

        {isTelegramActive ? (
          <div className="space-y-4 text-slate-700 text-sm leading-relaxed">
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
              <h3 className="font-bold text-emerald-800 mb-2">Telegram Bot Setup Complete!</h3>
              <p className="text-emerald-700 mb-4">Your bot is ready to receive messages. Here is how to use it:</p>
              
              <ol className="list-decimal list-inside space-y-2 text-emerald-900">
                <li>
                  Open the Telegram bot: {botUsername ? <strong className="font-mono">@{botUsername}</strong> : "your configured bot"}
                </li>
                <li>
                  Click <strong>Start</strong> or send: <code className="bg-emerald-100 px-1 py-0.5 rounded font-mono text-xs">/start</code>
                </li>
                <li>
                  Send any message to the bot.
                </li>
                <li>
                  The bot will trigger the configured default workflow.
                </li>
                <li>
                  The workflow result will be sent back as a Telegram reply.
                </li>
              </ol>

              {botUrl && (
                <div className="mt-4 pt-4 border-t border-emerald-200/50">
                  <span className="text-emerald-700 text-xs uppercase font-bold tracking-wider">Bot Link</span>
                  <a href={botUrl} target="_blank" rel="noreferrer" className="block mt-1 font-mono text-emerald-800 hover:text-emerald-600 transition-colors break-all">
                    {botUrl}
                  </a>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3 text-slate-600 text-sm leading-relaxed">
            <p>Follow these steps to configure your Telegram bot and connect it to a workflow run execution:</p>
            <ol className="list-decimal list-inside space-y-2">
              <li>
                Open Telegram and search for <strong className="text-slate-800">@BotFather</strong>. Send the command <code className="bg-slate-100 text-slate-700 px-1 py-0.5 rounded font-mono text-xs">/newbot</code> and follow instructions to create a bot.
              </li>
              <li>Copy the bot token.</li>
              <li>
                Add the following environment variables to your <code className="bg-slate-100 text-slate-700 px-1 py-0.5 rounded font-mono text-xs">.env</code> file:
                <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg font-mono text-xs my-2 overflow-x-auto leading-loose">
                  TELEGRAM_BOT_TOKEN=your_bot_token_here<br/>
                  DEFAULT_TELEGRAM_WORKFLOW_ID=your_workflow_id_here<br/>
                  TELEGRAM_BOT_USERNAME=your_bot_username_without_@
                </pre>
              </li>
              <li>Start the backend and Telegram worker.</li>
            </ol>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-100">
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 text-sm">Local development</h3>
            <p className="text-xs text-slate-500 mb-2">Run both processes locally to receive messages:</p>
            <div className="space-y-2">
              <div>
                <span className="text-xs font-semibold text-slate-600">Run backend:</span>
                <pre className="bg-slate-50 border border-slate-200 text-slate-800 p-2 rounded-lg font-mono text-xs mt-1 overflow-x-auto">
                  uvicorn app.main:app --reload
                </pre>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-600">Run Telegram worker (separate terminal):</span>
                <pre className="bg-slate-50 border border-slate-200 text-slate-800 p-2 rounded-lg font-mono text-xs mt-1 overflow-x-auto">
                  python -m app.channels.telegram_worker
                </pre>
              </div>
            </div>
          </div>
          
          <div className="space-y-2">
            <h3 className="font-bold text-slate-800 text-sm">Deployment / EasyPanel</h3>
            <p className="text-xs text-slate-500 mb-2">
              The Telegram worker should run as a separate service using the same codebase, database, and environment variables.
            </p>
            <div className="space-y-2">
              <div>
                <span className="text-xs font-semibold text-slate-600">Backend service command:</span>
                <pre className="bg-slate-50 border border-slate-200 text-slate-800 p-2 rounded-lg font-mono text-xs mt-1 overflow-x-auto">
                  uvicorn app.main:app --host 0.0.0.0 --port 8000
                </pre>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-600">Worker service command:</span>
                <pre className="bg-slate-50 border border-slate-200 text-slate-800 p-2 rounded-lg font-mono text-xs mt-1 overflow-x-auto">
                  python -m app.channels.telegram_worker
                </pre>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 flex items-start space-x-3 text-indigo-900 text-xs mt-6">
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
