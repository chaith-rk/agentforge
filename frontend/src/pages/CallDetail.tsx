import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Wifi, WifiOff, Download, PhoneOff } from 'lucide-react'
import { useCallWebSocket } from '../hooks/useCallWebSocket'
import { StatusBadge } from '../components/StatusBadge'
import { api, type CallResult } from '../lib/api'

function useTimer(running: boolean) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [running])
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function CallDetail() {
  const { id } = useParams<{ id: string }>()
  const ws = useCallWebSocket(id ?? null)
  const { transcript, collectedData, currentState, isConnected } = ws
  const [stopped, setStopped] = useState(false)
  const callCompleted = ws.callCompleted || stopped
  const transcriptEnd = useRef<HTMLDivElement>(null)
  const [result, setResult] = useState<CallResult | null>(null)
  const timer = useTimer(isConnected && !callCompleted)

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

  // Poll for result on completion
  useEffect(() => {
    if (!callCompleted || !id) return
    api.getCallResult(id).then(setResult).catch(() => null)
  }, [callCompleted, id])

  // Poll while active too
  useEffect(() => {
    if (!id || callCompleted) return
    const iv = setInterval(() => api.getCallResult(id).then(setResult).catch(() => null), 5000)
    return () => clearInterval(iv)
  }, [id, callCompleted])

  const downloadReport = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `verification-${id}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  const fields = result?.fields ?? collectedData.map((d) => ({
    field_name: d.field_name,
    display_name: d.display_name,
    candidate_value: d.candidate_value,
    employer_value: d.employer_value,
    status: d.status,
    match: d.match,
  }))

  const overallStatus = result?.overall_status ?? (callCompleted ? 'completed' : 'in_progress')

  return (
    <div className="flex flex-col h-full">
      {/* Status bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
        <div className="flex items-center gap-2">
          {isConnected ? (
            <><Wifi className="w-4 h-4 text-green-500" /><span className="text-xs text-green-600 font-medium">Live</span></>
          ) : callCompleted ? (
            <><WifiOff className="w-4 h-4 text-gray-400" /><span className="text-xs text-gray-500">Completed</span></>
          ) : (
            <><WifiOff className="w-4 h-4 text-gray-300" /><span className="text-xs text-gray-400">Connecting...</span></>
          )}
        </div>
        {currentState && (
          <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-1 rounded">{currentState}</span>
        )}
        {isConnected && <span className="text-sm font-mono text-gray-700">{timer}</span>}
        <div className="ml-auto flex items-center gap-3">
          {isConnected && !callCompleted && id && (
            <button
              onClick={() => api.stopCall(id).then(() => setStopped(true)).catch(() => null)}
              className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-800 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50"
            >
              <PhoneOff className="w-3.5 h-3.5" />
              End Call
            </button>
          )}
          <StatusBadge status={overallStatus} size="md" />
          {callCompleted && (
            <button onClick={downloadReport} className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-50">
              <Download className="w-3.5 h-3.5" />
              Download Report
            </button>
          )}
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Transcript */}
        <div className="flex-1 flex flex-col border-r border-gray-200 bg-gray-50">
          <div className="px-4 py-3 bg-white border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Transcript</h2>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-3">
            {transcript.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                {isConnected ? 'Waiting for conversation to begin...' : 'Connect to see live transcript'}
              </div>
            ) : (
              transcript.map((entry, i) => {
                const isAgent = entry.role === 'agent' || entry.role === 'assistant'
                return (
                  <div key={i} className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-xs lg:max-w-sm rounded-2xl px-3.5 py-2.5 text-sm ${isAgent ? 'bg-blue-600 text-white rounded-tl-sm' : 'bg-white text-gray-800 border border-gray-200 rounded-tr-sm'}`}>
                      <div className="text-xs font-medium mb-0.5 opacity-70">{isAgent ? 'Agent' : 'Employer'}</div>
                      {entry.content}
                    </div>
                  </div>
                )
              })
            )}
            <div ref={transcriptEnd} />
          </div>
        </div>

        {/* Verification results */}
        <div className="w-96 flex flex-col bg-white">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Verification Results</h2>
            {fields.length > 0 && <StatusBadge status={overallStatus} />}
          </div>
          <div className="flex-1 overflow-auto">
            {fields.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm p-4 text-center">
                Results will appear here as the agent collects information
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-2.5 font-medium text-gray-500">Field</th>
                    <th className="text-left px-3 py-2.5 font-medium text-gray-500">Claimed</th>
                    <th className="text-left px-3 py-2.5 font-medium text-gray-500">Confirmed</th>
                    <th className="text-left px-3 py-2.5 font-medium text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {fields.map((field, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-3 py-2.5 font-medium text-gray-700">{field.display_name || field.field_name}</td>
                      <td className="px-3 py-2.5 text-gray-500">{String(field.candidate_value ?? '—')}</td>
                      <td className="px-3 py-2.5 text-gray-700">{String(field.employer_value ?? '—')}</td>
                      <td className="px-3 py-2.5"><StatusBadge status={field.status || 'pending'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
