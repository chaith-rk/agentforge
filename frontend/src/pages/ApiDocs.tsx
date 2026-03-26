import { useState } from 'react'

const endpoints = [
  {
    method: 'POST', path: '/api/calls/initiate', description: 'Place a new verification call',
    curl: `curl -X POST http://localhost:8000/api/calls/initiate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: your-key" \\
  -d '{
    "agent_config_id": "employment_verification_v1",
    "subject_name": "John Smith",
    "phone_number": "+15551234567",
    "candidate_claims": {
      "employer_company_name": "Acme Corp",
      "position": "Engineer",
      "month_started": "January",
      "year_started": "2022"
    }
  }'`,
    python: `import requests

response = requests.post(
    "http://localhost:8000/api/calls/initiate",
    headers={"X-API-Key": "your-key"},
    json={
        "agent_config_id": "employment_verification_v1",
        "subject_name": "John Smith",
        "phone_number": "+15551234567",
        "candidate_claims": {
            "employer_company_name": "Acme Corp",
            "position": "Engineer",
        },
    }
)
session_id = response.json()["session_id"]`,
  },
  { method: 'GET', path: '/api/calls/{id}', description: 'Get call status and collected data', curl: 'curl http://localhost:8000/api/calls/{session_id} -H "X-API-Key: your-key"', python: 'result = requests.get(f"http://localhost:8000/api/calls/{session_id}", headers={"X-API-Key": "your-key"}).json()' },
  { method: 'GET', path: '/api/calls/{id}/result', description: 'Get structured side-by-side verification result', curl: 'curl http://localhost:8000/api/calls/{session_id}/result -H "X-API-Key: your-key"', python: 'result = requests.get(f"http://localhost:8000/api/calls/{session_id}/result", headers={"X-API-Key": "your-key"}).json()' },
  { method: 'GET', path: '/api/calls', description: 'List all calls with pagination', curl: 'curl "http://localhost:8000/api/calls?limit=10" -H "X-API-Key: your-key"', python: 'calls = requests.get("http://localhost:8000/api/calls?limit=10", headers={"X-API-Key": "your-key"}).json()' },
  { method: 'GET', path: '/api/agents', description: 'List all available agent configurations', curl: 'curl http://localhost:8000/api/agents -H "X-API-Key: your-key"', python: 'agents = requests.get("http://localhost:8000/api/agents", headers={"X-API-Key": "your-key"}).json()' },
  { method: 'WS', path: '/api/ws/{session_id}', description: 'WebSocket for real-time call events', curl: 'wscat -c ws://localhost:8000/api/ws/{session_id}', python: 'import websockets\nasync with websockets.connect(f"ws://localhost:8000/api/ws/{session_id}") as ws:\n    async for msg in ws: print(msg)' },
]

const comingSoon = [
  { title: 'Webhook Callbacks', desc: 'Register a URL to receive call completion notifications automatically' },
  { title: 'Batch API', desc: 'Upload a CSV with multiple verifications and receive results via webhook' },
  { title: 'MCP Server', desc: 'Connect Vetty Voice to any MCP-compatible AI assistant for verification workflows' },
]

const methodColors: Record<string, string> = {
  POST: 'bg-blue-100 text-blue-700',
  GET: 'bg-green-100 text-green-700',
  WS: 'bg-purple-100 text-purple-700',
}

export default function ApiDocs() {
  const [tab, setTab] = useState<'curl' | 'python'>('curl')
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">API Docs</h1>
      <p className="text-sm text-gray-500 mb-6">Integrate Vetty Voice into your workflow</p>

      {/* Auth */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 mb-6">
        <h2 className="font-semibold text-gray-900 mb-2">Authentication</h2>
        <p className="text-sm text-gray-600 mb-2">Include your API key in the <code className="bg-gray-200 px-1.5 py-0.5 rounded text-xs font-mono">X-API-Key</code> header on all requests.</p>
        <code className="block bg-gray-800 text-green-400 text-xs p-3 rounded-lg font-mono">X-API-Key: your-api-key</code>
      </div>

      {/* Endpoints */}
      <div className="space-y-3 mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900">Endpoints</h2>
          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
            {(['curl', 'python'] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} className={`px-3 py-1.5 font-medium transition-colors ${tab === t ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>{t}</button>
            ))}
          </div>
        </div>
        {endpoints.map((ep) => (
          <div key={ep.path} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              className="w-full text-left flex items-center gap-3 px-5 py-4 hover:bg-gray-50"
              onClick={() => setExpanded(expanded === ep.path ? null : ep.path)}
            >
              <span className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${methodColors[ep.method] ?? 'bg-gray-100 text-gray-600'}`}>{ep.method}</span>
              <code className="text-sm font-mono text-gray-800">{ep.path}</code>
              <span className="text-sm text-gray-500 ml-2">{ep.description}</span>
            </button>
            {expanded === ep.path && (
              <div className="border-t border-gray-100 px-5 pb-4">
                <pre className="bg-gray-900 text-green-400 text-xs p-4 rounded-lg mt-3 overflow-x-auto font-mono whitespace-pre">
                  {tab === 'curl' ? ep.curl : ep.python}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Coming soon */}
      <h2 className="font-semibold text-gray-900 mb-3">Coming Soon</h2>
      <div className="grid grid-cols-3 gap-4">
        {comingSoon.map(({ title, desc }) => (
          <div key={title} className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-sm text-gray-700">{title}</span>
              <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full">Soon</span>
            </div>
            <p className="text-xs text-gray-500">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
