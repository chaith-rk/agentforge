import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { History } from 'lucide-react'
import { api, type Call } from '../lib/api'
import { StatusBadge } from '../components/StatusBadge'

function formatDate(iso: string) {
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return iso }
}

export default function CallHistory() {
  const navigate = useNavigate()
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getCalls(50)
      .then(setCalls)
      .catch(() => setError('Failed to load call history'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Call History</h1>
      <p className="text-sm text-gray-500 mb-6">All verification calls</p>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-4 rounded-lg mb-4">{error}</div>}

      <div className="bg-white rounded-xl border border-gray-200">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading...</div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No calls yet</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Agent', 'Candidate', 'Outcome', 'Status', 'Session ID'].map((h) => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {calls.map((call) => (
                <tr
                  key={call.session_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/calls/${call.session_id}`)}
                >
                  <td className="px-5 py-3.5 text-gray-500">{formatDate(call.created_at)}</td>
                  <td className="px-5 py-3.5 text-gray-600">{call.agent_config_id?.replace('_v1', '').replace(/_/g, ' ') || '—'}</td>
                  <td className="px-5 py-3.5 font-medium text-gray-900">{(call.collected_data?.subject_name as string) || '—'}</td>
                  <td className="px-5 py-3.5 text-gray-500">{call.outcome}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={call.status || call.outcome || 'pending'} /></td>
                  <td className="px-5 py-3.5 font-mono text-xs text-gray-400">{call.session_id.slice(0, 8)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
