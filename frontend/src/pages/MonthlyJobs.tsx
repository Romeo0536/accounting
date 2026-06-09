import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, CheckSquare, Square } from 'lucide-react'
import { getMonthlyJobs, updateMonthlyJob, bulkCreateMonthlyJobs } from '../api'
import type { MonthlyJob } from '../types'
import { MONTH_NAMES_TH } from '../types'
import StatusBadge from '../components/StatusBadge'

const STEPS = [
  { key: 'documents_received', label: 'รับเอกสาร', short: 'เอกสาร' },
  { key: 'bookkeeping_done', label: 'บันทึกบัญชี', short: 'บัญชี' },
  { key: 'vat_filed', label: 'ยื่น ภพ.30', short: 'ภพ.30' },
  { key: 'wht_filed', label: 'ยื่น ภงด.', short: 'ภงด.' },
  { key: 'sso_filed', label: 'ประกันสังคม', short: 'ปกส.' },
  { key: 'financial_statement_done', label: 'จัดทำงบ', short: 'งบ' },
] as const

type StepKey = typeof STEPS[number]['key']

export default function MonthlyJobs() {
  const qc = useQueryClient()
  const today = new Date()
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [year, setYear] = useState(today.getFullYear())

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['monthly-jobs-all', month, year],
    queryFn: () => getMonthlyJobs({ month, year }),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<MonthlyJob> }) => updateMonthlyJob(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['monthly-jobs-all', month, year] }),
  })

  const bulkMut = useMutation({
    mutationFn: () => bulkCreateMonthlyJobs(month, year),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['monthly-jobs-all', month, year] })
      alert(`สร้างงานใหม่ ${data.created} ราย`)
    },
  })

  const toggle = (job: MonthlyJob, key: StepKey) => {
    updateMut.mutate({ id: job.id, data: { [key]: !job[key] } })
  }

  const completed = jobs.filter((j: MonthlyJob) => j.status === 'completed').length
  const total = jobs.length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">งานประจำเดือน</h1>
          <p className="text-gray-500 text-sm mt-1">เสร็จแล้ว {completed}/{total} ราย</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-auto" value={month} onChange={e => setMonth(+e.target.value)}>
            {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
          </select>
          <input className="input w-24" type="number" value={year} onChange={e => setYear(+e.target.value)} />
          <button
            className="btn-secondary flex items-center gap-2"
            onClick={() => bulkMut.mutate()}
            disabled={bulkMut.isPending}
          >
            <RefreshCw className="w-4 h-4" />
            สร้างงานเดือนนี้
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>ความคืบหน้า</span>
            <span>{Math.round(completed / total * 100)}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-500"
              style={{ width: `${completed / total * 100}%` }}
            />
          </div>
        </div>
      )}

      {isLoading && <div className="text-center py-8 text-gray-400">กำลังโหลด...</div>}

      {!isLoading && jobs.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="mb-3">ยังไม่มีงานเดือน {MONTH_NAMES_TH[month]} {year + 543}</p>
          <button className="btn-primary" onClick={() => bulkMut.mutate()}>
            สร้างงานสำหรับลูกค้าทั้งหมด
          </button>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">ลูกค้า</th>
                  {STEPS.map(s => (
                    <th key={s.key} className="px-3 py-3 text-center text-xs font-semibold text-gray-500 uppercase whitespace-nowrap">
                      {s.short}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job: MonthlyJob) => (
                  <tr key={job.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{job.client?.name}</div>
                      <div className="text-xs text-gray-400">{job.client?.code}</div>
                    </td>
                    {STEPS.map(s => (
                      <td key={s.key} className="px-3 py-3 text-center">
                        <button
                          onClick={() => toggle(job, s.key)}
                          disabled={updateMut.isPending}
                          className="p-1 rounded hover:bg-gray-100 transition-colors"
                          title={s.label}
                        >
                          {job[s.key] ? (
                            <CheckSquare className="w-5 h-5 text-green-500" />
                          ) : (
                            <Square className="w-5 h-5 text-gray-300" />
                          )}
                        </button>
                      </td>
                    ))}
                    <td className="px-4 py-3 text-center">
                      <StatusBadge status={job.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        {STEPS.map(s => (
          <div key={s.key} className="flex items-center gap-1">
            <CheckSquare className="w-3.5 h-3.5 text-green-500" />
            {s.label}
          </div>
        ))}
      </div>
    </div>
  )
}
