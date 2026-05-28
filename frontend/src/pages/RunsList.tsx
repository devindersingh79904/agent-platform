import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { getRunsPaginated, getWorkflows } from '../api/client';
import { APP_ROUTES } from '../constants/appRoutes';
import { Activity, ExternalLink, Calendar, RefreshCcw, Filter, ChevronLeft, ChevronRight, Clock } from 'lucide-react';

const RunsList = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Extract page and query filters from URL search params
  const workflowIdParam = searchParams.get('workflowId') || '';
  const statusParam = searchParams.get('status') || '';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);

  const [runs, setRuns] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [workflowMap, setWorkflowMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination states
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const size = 15; // Set page size to 15 items

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'QUEUED', label: 'Queued' },
    { value: 'RUNNING', label: 'Running' },
    { value: 'WAITING_INPUT', label: 'Waiting Input' },
    { value: 'COMPLETED', label: 'Completed' },
    { value: 'FAILED', label: 'Failed' },
    { value: 'CANCELLED', label: 'Cancelled' },
  ];

  // Fetch all workflows on mount to build id-to-name mapping and populate dropdown filter
  useEffect(() => {
    getWorkflows()
      .then((data) => {
        setWorkflows(data);
        const mapping: Record<string, string> = {};
        data.forEach((wf: any) => {
          mapping[wf.id] = wf.name;
        });
        setWorkflowMap(mapping);
      })
      .catch((err) => {
        console.error('Failed to load workflows', err);
      });
  }, []);

  const loadRuns = () => {
    setLoading(true);
    setError(null);
    getRunsPaginated(pageParam, size, {
      workflowId: workflowIdParam || undefined,
      status: statusParam || undefined,
    })
      .then((res) => {
        setRuns(res.content || []);
        // Access paginated values correctly from res.pagination
        const totalElements = res.pagination?.total_elements ?? 0;
        const pages = res.pagination?.total_pages ?? 1;
        setTotalItems(totalElements);
        setTotalPages(pages);
      })
      .catch((err) => {
        console.error('Failed to fetch runs', err);
        setError('Failed to load workflow runs. Please try again.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  // Re-fetch runs whenever any filter or pagination parameter changes
  useEffect(() => {
    loadRuns();
  }, [workflowIdParam, statusParam, pageParam]);

  const handleWorkflowChange = (wfId: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (wfId) {
      newParams.set('workflowId', wfId);
    } else {
      newParams.delete('workflowId');
    }
    newParams.set('page', '1'); // Reset to page 1 on filter change
    setSearchParams(newParams);
  };

  const handleStatusChange = (status: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (status) {
      newParams.set('status', status);
    } else {
      newParams.delete('status');
    }
    newParams.set('page', '1'); // Reset to page 1 on filter change
    setSearchParams(newParams);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return;
    const newParams = new URLSearchParams(searchParams);
    newParams.set('page', newPage.toString());
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border border-rose-200';
      case 'RUNNING':
        return 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse';
      case 'QUEUED':
        return 'bg-amber-50 text-amber-700 border border-amber-200';
      case 'WAITING_INPUT':
        return 'bg-purple-50 text-purple-700 border border-purple-200';
      case 'CANCELLED':
        return 'bg-slate-100 text-slate-700 border border-slate-300';
      default:
        return 'bg-slate-50 text-slate-600 border border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <Activity size={28} className="text-indigo-500" />
          Workflow Runs
        </h1>
        <button
          onClick={loadRuns}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors font-medium text-sm border border-slate-200 shadow-sm"
        >
          <RefreshCcw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Premium Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-slate-600 font-medium text-sm">
            <Filter size={16} className="text-slate-400" />
            Filters:
          </div>

          {/* Workflow Filter Dropdown */}
          <select
            value={workflowIdParam}
            onChange={(e) => handleWorkflowChange(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
          >
            <option value="">All Workflows</option>
            {workflows.map((wf) => (
              <option key={wf.id} value={wf.id}>
                {wf.name}
              </option>
            ))}
          </select>

          {/* Status Filter Dropdown */}
          <select
            value={statusParam}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Clear Filters Helper */}
          {(workflowIdParam || statusParam) && (
            <button
              onClick={clearFilters}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
        <div className="text-xs font-medium text-slate-505 font-mono">
          Total: {totalItems} {totalItems === 1 ? 'run' : 'runs'}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={loadRuns} className="underline text-rose-800 text-sm font-medium">Retry</button>
        </div>
      )}

      {/* Table grid block */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full mb-4"></div>
            <div>Loading workflow runs...</div>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center space-y-4">
            <Activity size={40} className="mx-auto text-slate-300" />
            <p className="text-slate-505 text-lg">No workflow runs found.</p>
            {(workflowIdParam || statusParam) && (
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg text-sm font-medium transition"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="p-4 font-semibold text-slate-600 text-sm">Run ID</th>
                  <th className="p-4 font-semibold text-slate-600 text-sm">Workflow</th>
                  <th className="p-4 font-semibold text-slate-600 text-sm">Started At</th>
                  <th className="p-4 font-semibold text-slate-600 text-sm">Completed At</th>
                  <th className="p-4 font-semibold text-slate-600 text-sm">Status</th>
                  <th className="p-4 font-semibold text-slate-600 text-sm text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4">
                      <Link
                        to={APP_ROUTES.RUN_MONITOR(run.id)}
                        className="font-mono text-sm text-indigo-600 hover:text-indigo-800 hover:underline font-medium"
                      >
                        {run.id}
                      </Link>
                    </td>
                    <td className="p-4">
                      {run.workflow_id ? (
                        <Link
                          to={APP_ROUTES.WORKFLOW_BUILDER(run.workflow_id)}
                          className="font-medium text-slate-900 hover:text-indigo-600 hover:underline"
                        >
                          {workflowMap[run.workflow_id] || 'Loading...'}
                        </Link>
                      ) : (
                        <span className="italic text-slate-400">Deleted Workflow</span>
                      )}
                    </td>
                    <td className="p-4 text-slate-600 text-sm">
                      <div className="flex items-center gap-1.5">
                        <Calendar size={14} className="text-slate-400" />
                        {run.started_at ? new Date(run.started_at).toLocaleString() : 'Pending'}
                      </div>
                    </td>
                    <td className="p-4 text-slate-600 text-sm">
                      {run.completed_at ? (
                        <div className="flex items-center gap-1.5">
                          <Calendar size={14} className="text-slate-400" />
                          {new Date(run.completed_at).toLocaleString()}
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-slate-400 italic">
                          <Clock size={14} />
                          {run.status === 'RUNNING' ? 'Running' : '—'}
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${getStatusBadgeClass(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => navigate(APP_ROUTES.RUN_MONITOR(run.id))}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-xs font-semibold border border-slate-200 shadow-sm transition-colors"
                      >
                        <ExternalLink size={12} />
                        Monitor
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Premium Pagination Footer Controls */}
        {!loading && totalPages > 1 && (
          <div className="bg-slate-50 border-t border-slate-200 px-4 py-3 flex items-center justify-between sm:px-6">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                disabled={pageParam === 1}
                onClick={() => handlePageChange(pageParam - 1)}
                className="relative inline-flex items-center px-4 py-2 border border-slate-300 text-sm font-medium rounded-md text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={pageParam === totalPages}
                onClick={() => handlePageChange(pageParam + 1)}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-slate-300 text-sm font-medium rounded-md text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>

            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-slate-700">
                  Showing page <span className="font-semibold">{pageParam}</span> of{' '}
                  <span className="font-semibold">{totalPages}</span>
                </p>
              </div>

              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    disabled={pageParam === 1}
                    onClick={() => handlePageChange(pageParam - 1)}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-slate-300 bg-white text-sm font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <ChevronLeft size={16} />
                  </button>

                  {Array.from({ length: totalPages }).map((_, index) => {
                    const pageNum = index + 1;
                    // Format pagination numbers with ellipsis (...) for large page counts
                    if (
                      totalPages > 6 &&
                      Math.abs(pageNum - pageParam) > 2 &&
                      pageNum !== 1 &&
                      pageNum !== totalPages
                    ) {
                      if (pageNum === 2 || pageNum === totalPages - 1) {
                        return (
                          <span key={pageNum} className="relative inline-flex items-center px-3 py-2 border border-slate-300 bg-white text-sm font-medium text-slate-500">
                            ...
                          </span>
                        );
                      }
                      return null;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`relative inline-flex items-center px-3.5 py-2 border text-sm font-semibold transition-colors ${
                          pageParam === pageNum
                            ? 'z-10 bg-indigo-600 border-indigo-600 text-white'
                            : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}

                  <button
                    disabled={pageParam === totalPages}
                    onClick={() => handlePageChange(pageParam + 1)}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-slate-300 bg-white text-sm font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <ChevronRight size={16} />
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RunsList;
