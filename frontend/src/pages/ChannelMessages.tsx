import { useEffect, useState } from 'react';
import { MessageCircle, ExternalLink } from 'lucide-react';
import { getChannelMessages } from '../api/client';

const ChannelMessages = () => {
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMessages();
  }, []);

  const fetchMessages = async () => {
    try {
      setLoading(true);
      const data = await getChannelMessages(1, 100);
      setMessages(data);
    } catch (err: any) {
      setError("Failed to fetch messages: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <MessageCircle className="text-indigo-600" />
          Channel Messages
        </h1>
        <button onClick={fetchMessages} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors w-full sm:w-auto">
          Refresh
        </button>
      </div>

      {loading && <div className="text-slate-500">Loading messages...</div>}
      {error && <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-lg">{error}</div>}

      {!loading && !error && messages.length === 0 && (
        <div className="text-slate-500 bg-white border border-slate-200 p-8 rounded-xl text-center">
          No channel messages found. Connect Telegram or another channel to see messages here.
        </div>
      )}

      {!loading && messages.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex-1">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="p-4 font-semibold">Channel</th>
                  <th className="p-4 font-semibold">Direction</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold">External ID</th>
                  <th className="p-4 font-semibold">Run ID</th>
                  <th className="p-4 font-semibold">Payload</th>
                  <th className="p-4 font-semibold">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {messages.map((msg) => (
                  <tr key={msg.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4 font-semibold text-slate-800">{msg.channel_type}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        msg.direction === 'INBOUND' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {msg.direction}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        msg.status === 'RECEIVED' ? 'bg-amber-100 text-amber-700' :
                        msg.status === 'PROCESSED' || msg.status === 'SENT' ? 'bg-emerald-100 text-emerald-700' :
                        'bg-rose-100 text-rose-700'
                      }`}>
                        {msg.status}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-xs text-slate-500">{msg.external_message_id}</td>
                    <td className="p-4">
                      {msg.run_id ? (
                        <a href={`/runs/${msg.run_id}`} className="text-indigo-600 hover:underline flex items-center gap-1 font-mono text-xs">
                          {msg.run_id.slice(0,8)} <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span className="text-slate-400 text-xs">N/A</span>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="max-w-xs truncate text-xs font-mono bg-slate-100 p-2 rounded text-slate-700">
                        {msg.payload_json}
                      </div>
                    </td>
                    <td className="p-4 text-slate-500 whitespace-nowrap">
                      {new Date(msg.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChannelMessages;
