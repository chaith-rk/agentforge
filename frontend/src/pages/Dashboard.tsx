import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Phone, CheckCircle, Activity, Clock, Plus } from 'lucide-react'
import { api, type CallStats, type Call } from '../lib/api'
import { StatusBadge } from '../components/StatusBadge'

function StatCard({ icon: Icon, label, value, sub, color }: { icon: React.ElementType; label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500 font-medium">{label}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

function formatDate(iso: string) {
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return iso }
}

function formatDuration(secs: number) {
  if (!secs) return '—'
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function Dashboard() {
  const [stats, setStats] = useState<CallStats | null>(null)
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getStats(), api.getCalls(10)])
      .then(([s, c]) => { setStats(s); setCalls(c) })
      .catch(() => setError('Backend not reachable. Start the server with: uvicorn src.main:app --reload'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Overview of all verification calls</p>
        </div>
        <Link to="/calls/new" className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4" />
          New Call
        </Link>
      </div>

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard icon={Phone} label="Total Calls" value={loading ? '—' : (stats?.total_calls ?? 0)} sub={`${stats?.calls_today ?? 0} today`} color="bg-blue-50 text-blue-600" />
        <StatCard icon={CheckCircle} label="Success Rate" value={loading ? '—' : `${Math.round((stats?.success_rate ?? 0) * 100)}%`} sub="completed calls" color="bg-green-50 text-green-600" />
        <StatCard icon={Activity} label="Active Calls" value={loading ? '—' : (stats?.active_calls ?? 0)} sub="right now" color="bg-purple-50 text-purple-600" />
        <StatCard icon={Clock} label="Avg Duration" value={loading ? '—' : formatDuration(stats?.avg_duration_seconds ?? 0)} sub="per call" color="bg-orange-50 text-orange-600" />
      </div>

      {/* Recent calls */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Recent Calls</h2>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading...</div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <Phone className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No calls yet</p>
            <p className="text-gray-400 text-sm mt-1">Place your first verification call to see it here.</p>
            <Link to="/calls/new" className="inline-flex items-center gap-1.5 mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
              <Plus className="w-3.5 h-3.5" /> Place Call
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Candidate', 'Agent', 'State', 'Outcome', 'Status'].map((h) => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {calls.map((call) => (
                <tr key={call.session_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => window.location.href = `/calls/${call.session_id}`}>
                  <td className="px-5 py-3.5 text-gray-500">{formatDate(call.created_at)}</td>
                  <td className="px-5 py-3.5 font-medium text-gray-900">{(call.collected_data?.subject_name as string) || '—'}</td>
                  <td className="px-5 py-3.5 text-gray-500">{call.agent_config_id?.replace('_v1', '').replace(/_/g, ' ') || '—'}</td>
                  <td className="px-5 py-3.5 text-gray-500 font-mono text-xs">{call.current_state}</td>
                  <td className="px-5 py-3.5 text-gray-500">{call.outcome}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={call.status || call.outcome || 'pending'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
