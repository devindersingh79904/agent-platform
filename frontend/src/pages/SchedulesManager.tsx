import React, { useEffect, useState } from 'react';
import { Clock, Play, Trash2, Edit2, CheckCircle2, XCircle, Plus } from 'lucide-react';
import { getSchedules, deleteSchedule, triggerSchedule, updateSchedule, createSchedule, getWorkflows } from '../api/client';
import { Link } from 'react-router-dom';

const SchedulesManager: React.FC = () => {
  const [schedules, setSchedules] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    workflow_id: '',
    cron_expression: '* * * * *',
    enabled: true,
  });

  useEffect(() => {
    fetchSchedules();
    fetchWorkflows();
  }, []);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const data = await getSchedules(1, 100);
      setSchedules(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchWorkflows = async () => {
    try {
      const data = await getWorkflows(1, 100);
      setWorkflows(data);
      if (data.length > 0) {
        setFormData(prev => ({ ...prev, workflow_id: data[0].id }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete schedule?")) return;
    try {
      await deleteSchedule(id);
      fetchSchedules();
    } catch (err) {
      console.error(err);
      alert("Failed to delete schedule");
    }
  };

  const handleTrigger = async (id: string) => {
    try {
      await triggerSchedule(id);
      alert("Schedule triggered manually!");
    } catch (err: any) {
      console.error(err);
      alert("Failed to trigger: " + err.message);
    }
  };

  const handleToggle = async (id: string, currentEnabled: boolean) => {
    try {
      await updateSchedule(id, { enabled: !currentEnabled });
      fetchSchedules();
    } catch (err) {
      console.error(err);
      alert("Failed to update status");
    }
  };

  const openModal = (schedule?: any) => {
    if (schedule) {
      setEditingId(schedule.id);
      setFormData({
        name: schedule.name,
        workflow_id: schedule.workflow_id,
        cron_expression: schedule.cron_expression,
        enabled: schedule.enabled,
      });
    } else {
      setEditingId(null);
      setFormData({
        name: '',
        workflow_id: workflows.length > 0 ? workflows[0].id : '',
        cron_expression: '* * * * *',
        enabled: true,
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await updateSchedule(editingId, formData);
      } else {
        await createSchedule(formData);
      }
      setIsModalOpen(false);
      fetchSchedules();
    } catch (err: any) {
      console.error(err);
      alert("Failed to save schedule: " + err.message);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Clock className="text-indigo-600" />
          Schedules Manager
        </h1>
        <button onClick={() => openModal()} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2">
          <Plus size={18} /> New Schedule
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
              <th className="py-4 px-6">Name / CRON</th>
              <th className="py-4 px-6">Workflow</th>
              <th className="py-4 px-6">Status</th>
              <th className="py-4 px-6">Last Run / Next Run</th>
              <th className="py-4 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                <td className="py-4 px-6">
                  <div className="font-bold text-slate-800">{s.name}</div>
                  <div className="font-mono text-sm text-slate-500">{s.cron_expression}</div>
                </td>
                <td className="py-4 px-6 font-mono text-sm text-indigo-600">
                  <Link to={`/workflows/${s.workflow_id}`} className="hover:underline">{s.workflow_id.slice(0,8)}...</Link>
                </td>
                <td className="py-4 px-6">
                  <button onClick={() => handleToggle(s.id, s.enabled)} className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold transition-colors ${s.enabled ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                    {s.enabled ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                    {s.enabled ? 'Active' : 'Disabled'}
                  </button>
                </td>
                <td className="py-4 px-6 text-xs text-slate-500">
                  <div>Last: {s.last_run_at ? new Date(s.last_run_at).toLocaleString() : 'Never'}</div>
                  <div>Next: {s.next_run_at ? new Date(s.next_run_at).toLocaleString() : 'Unknown'}</div>
                </td>
                <td className="py-4 px-6 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => handleTrigger(s.id)} className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Trigger Now">
                      <Play size={18} />
                    </button>
                    <button onClick={() => openModal(s)} className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors" title="Edit">
                      <Edit2 size={18} />
                    </button>
                    <button onClick={() => handleDelete(s.id)} className="p-2 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors" title="Delete">
                      <Trash2 size={18} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && schedules.length === 0 && (
              <tr>
                <td colSpan={5} className="py-12 text-center text-slate-500">No schedules configured.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">{editingId ? 'Edit Schedule' : 'Create Schedule'}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Name</label>
                <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5" />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Workflow</label>
                <select required value={formData.workflow_id} onChange={e => setFormData({...formData, workflow_id: e.target.value})} className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5">
                  {workflows.map(w => <option key={w.id} value={w.id}>{w.name} ({w.id.slice(0,8)})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">CRON Expression</label>
                <input required type="text" value={formData.cron_expression} onChange={e => setFormData({...formData, cron_expression: e.target.value})} className="w-full font-mono bg-slate-50 border border-slate-300 rounded-lg p-2.5" placeholder="* * * * *" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="enabled" checked={formData.enabled} onChange={e => setFormData({...formData, enabled: e.target.checked})} className="rounded text-indigo-600 focus:ring-indigo-500" />
                <label htmlFor="enabled" className="text-sm font-semibold text-slate-700">Enabled</label>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-semibold">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SchedulesManager;
