interface Props {
  summary?: string
  pending?: boolean
}

export function CallSummary({ summary, pending = false }: Props) {
  return (
    <div className="px-6 py-5 border-b border-gray-100">
      <h3 className="text-lg font-bold text-gray-900 mb-3">Call Summary</h3>
      {pending && !summary ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-gray-100 rounded w-full" />
          <div className="h-3 bg-gray-100 rounded w-5/6" />
          <div className="h-3 bg-gray-100 rounded w-2/3" />
        </div>
      ) : summary ? (
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{summary}</p>
      ) : (
        <p className="text-sm text-gray-400 italic">No summary available for this call.</p>
      )}
    </div>
  )
}
