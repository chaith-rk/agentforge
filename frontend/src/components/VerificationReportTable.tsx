import type { FieldVerification } from '../lib/api'
import { StatusBadge } from './StatusBadge'

interface Props {
  fields: FieldVerification[]
}

const confidenceStyles: Record<string, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-red-100 text-red-800',
}

function ConfidencePill({ confidence }: { confidence?: string | null }) {
  if (!confidence) {
    return <span className="text-gray-400">—</span>
  }
  const cls = confidenceStyles[confidence.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
  const label = confidence.charAt(0).toUpperCase() + confidence.slice(1).toLowerCase()
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

export function VerificationReportTable({ fields }: Props) {
  if (fields.length === 0) {
    return (
      <div className="px-6 py-8 text-center text-sm text-gray-400">
        No verification data collected on this call.
      </div>
    )
  }

  return (
    <div className="px-6 py-5">
      <h3 className="text-lg font-bold text-gray-900 mb-4">Verification Details</h3>
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <Th>Question</Th>
              <Th>Prior Answer</Th>
              <Th>Call Answer</Th>
              <Th>Status</Th>
              <Th>Confidence</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {fields.map((field, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-3 py-3 align-top text-gray-800 max-w-xs">
                  <div className="font-medium">{field.display_name || field.field_name}</div>
                  {field.question && (
                    <div className="text-xs text-gray-500 mt-0.5">{field.question}</div>
                  )}
                </td>
                <td className="px-3 py-3 align-top text-gray-600">
                  {renderValue(field.candidate_value)}
                </td>
                <td className="px-3 py-3 align-top text-gray-800">
                  {renderValue(field.employer_value)}
                </td>
                <td className="px-3 py-3 align-top">
                  <StatusBadge status={field.status || 'pending'} />
                </td>
                <td className="px-3 py-3 align-top">
                  <ConfidencePill confidence={field.confidence} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-3 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
      {children}
    </th>
  )
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}
