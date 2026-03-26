import { useState } from 'react'
import { Copy, Check, Key, Webhook, Cpu } from 'lucide-react'

export default function Settings() {
  const [copied, setCopied] = useState(false)
  const apiKey = 'dev-key'
  const masked = apiKey.slice(0, 3) + '•'.repeat(16)

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-6">API keys and integration configuration</p>

      <div className="space-y-4">
        {/* API Key */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
              <Key className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="font-semibold text-gray-900">API Key</h2>
          </div>
          <p className="text-sm text-gray-500 mb-3">Include this key in the <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono">X-API-Key</code> header for all API requests.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-700">{masked}</code>
            <button
              onClick={copyKey}
              className="flex items-center gap-1.5 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Webhook */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 opacity-60">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                <Webhook className="w-4 h-4 text-gray-500" />
              </div>
              <h2 className="font-semibold text-gray-700">Webhook URL</h2>
            </div>
            <span className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full font-medium">Coming Soon</span>
          </div>
          <p className="text-sm text-gray-500">Register a URL to receive call completion notifications. Vetty will POST structured results to your endpoint within seconds of call completion.</p>
        </div>

        {/* MCP */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 opacity-60">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                <Cpu className="w-4 h-4 text-gray-500" />
              </div>
              <h2 className="font-semibold text-gray-700">MCP Server</h2>
            </div>
            <span className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full font-medium">Coming Soon</span>
          </div>
          <p className="text-sm text-gray-500">Connect Vetty Voice to any MCP-compatible AI assistant. Trigger verifications and retrieve results from Claude, Cursor, or any MCP client.</p>
        </div>
      </div>
    </div>
  )
}
