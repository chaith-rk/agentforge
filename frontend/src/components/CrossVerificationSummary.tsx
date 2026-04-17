interface Props {
  confirmed: number
  toClarify: number
  contradictions: number
}

export function CrossVerificationSummary({ confirmed, toClarify, contradictions }: Props) {
  return (
    <div className="px-6 py-5">
      <h3 className="text-lg font-bold text-gray-900 mb-4">Cross-Verification Summary</h3>
      <div className="border-t border-gray-200 pt-4 grid grid-cols-3 gap-4">
        <SummaryCard value={confirmed} label="Confirmed Facts" valueClass="text-green-500" />
        <SummaryCard value={toClarify} label="Items to Clarify" valueClass="text-amber-500" />
        <SummaryCard value={contradictions} label="Contradictions" valueClass="text-red-500" />
      </div>
    </div>
  )
}

function SummaryCard({ value, label, valueClass }: { value: number; label: string; valueClass: string }) {
  return (
    <div className="border border-gray-200 rounded-lg py-6 px-4 flex flex-col items-center justify-center text-center">
      <div className={`text-4xl font-bold ${valueClass}`}>{value}</div>
      <div className="text-sm text-gray-500 font-medium mt-2">{label}</div>
    </div>
  )
}
