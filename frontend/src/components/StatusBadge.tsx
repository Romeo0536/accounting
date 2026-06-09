interface Props {
  status: string
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  active: { label: 'ใช้งาน', className: 'badge-green' },
  inactive: { label: 'ไม่ใช้งาน', className: 'badge-gray' },
  pending: { label: 'รอดำเนินการ', className: 'badge-gray' },
  in_progress: { label: 'กำลังดำเนินการ', className: 'badge-blue' },
  completed: { label: 'เสร็จแล้ว', className: 'badge-green' },
  overdue: { label: 'เกินกำหนด', className: 'badge-red' },
  draft: { label: 'ร่าง', className: 'badge-gray' },
  sent: { label: 'ส่งแล้ว', className: 'badge-blue' },
  paid: { label: 'ชำระแล้ว', className: 'badge-green' },
  filed: { label: 'ยื่นแล้ว', className: 'badge-green' },
}

export default function StatusBadge({ status }: Props) {
  const config = STATUS_CONFIG[status] || { label: status, className: 'badge-gray' }
  return <span className={config.className}>{config.label}</span>
}
