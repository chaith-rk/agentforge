interface Props {
  status: string
  size?: 'sm' | 'md'
}

const styles: Record<string, string> = {
  verified: 'bg-green-100 text-green-800',
  completed: 'bg-green-100 text-green-800',
  review_needed: 'bg-amber-100 text-amber-800',
  unable_to_verify: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-800',
  pending: 'bg-gray-100 text-gray-400',
  refused: 'bg-red-100 text-red-800',
  redirected: 'bg-purple-100 text-purple-800',
  voicemail: 'bg-yellow-100 text-yellow-800',
  no_record: 'bg-orange-100 text-orange-800',
  dead_end: 'bg-gray-100 text-gray-600',
  active: 'bg-green-100 text-green-800',
  draft: 'bg-gray-100 text-gray-600',
}

const labels: Record<string, string> = {
  verified: 'Verified',
  completed: 'Completed',
  review_needed: 'Review Needed',
  unable_to_verify: 'Unable to Verify',
  in_progress: 'In Progress',
  pending: 'Pending',
  refused: 'Refused',
  redirected: 'Redirected',
  voicemail: 'Voicemail',
  no_record: 'No Record',
  dead_end: 'Dead End',
  active: 'Active',
  draft: 'Draft',
}

export function StatusBadge({ status, size = 'sm' }: Props) {
  const cls = styles[status] || 'bg-gray-100 text-gray-600'
  const textSize = size === 'md' ? 'text-sm px-3 py-1' : 'text-xs px-2.5 py-0.5'
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${textSize} ${cls}`}>
      {labels[status] || status}
    </span>
  )
}
