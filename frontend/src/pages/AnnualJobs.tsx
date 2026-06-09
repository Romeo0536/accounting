import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, CheckSquare, Square } from 'lucide-react'
import { getAnnualJobs, updateAnnualJob, bulkCreateAnnualJobs } from '../api'
import type { AnnualJob } from '../types'
import StatusBadge from '../components/StatusBadge'

const STEPS = [
  { key: 'annual_fs_done', label: 'งบการเงินประจำปี' },
  { key: 'pnd51_filed', label: 'ยื่น ภงด.51' },
  { key: 'pnd50_filed', label: 'ยื่น ภงด.50' },
  { key: 'boj5_filed', label: 'ยื่น บอจ.5' },
  { key: 'audit_done', label: 'ตรวจสอบบัญชี' },
] as const

type StepKey = typeof STEPS[number]['key']

export default function AnnualJobs() {
  const qc = useQueryClient()
  const [year, setYear] = useState(new Date().getFullYear())

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['annual-jobs-all', year],
    queryFn: () => getAnnualJobs({ year }),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<AnnualJob> }) => updateAnnualJob(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['annual-jobs-all', year] }),
  })

  const bulkMut = useMutation({
    mutationFn: () => bulkCreateAnnualJobs(year),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['annual-jobs-all', year] })
      alert(`สร้างงานประจำปีใหม่ ${data.created} ราย`)
    },
  })

  const toggle = (job: AnnualJob, key: StepKey) => {
    updateMut.mutate({ id: job.id, data: { [key]: !job[key] } })
  }

  const completed = jobs.filter((j: AnnualJob) => j.status === 'completed').length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">งานประจำปี</h1>
          <p className="text-gray-500 text-sm mt-1">เสร็จแล้ว {completed}/{jobs.length} ราย</p>
        </div>
        <div className="flex items-center gap-3">
          <input className="input w-28" type="number" value={year} onChange={e => setYear(+e.target.value)} placeholder="ปี พ.ศ." />
          <button className="btn-secondary flex items-center gap-2" onClick={() => bulkMut.mutate()} disabled={bulkMut.isPending}>
            <RefreshCw className="w-4 h-4" /> สร้างงานปีนี้
          </button>
        </div>
      </div>

      {isLoading && <div className="text-center py-8 text-gray-400">กำลังโหลด...</div>}

      {!isLoading && jobs.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p className="mb-3">ยังไม่มีงานปี {year}</p>
          <button className="btn-primary" onClick={() => bulkMut.mutate()}>สร้างงานสำหรับลูกค้าทั้งหมด</button>
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
                      {s.label}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">ตรวจสอบ</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job: AnnualJob) => (
                  <tr key={job.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{job.client?.name}</div>
                      <div className="text-xs text-gray-400">{job.client?.code}</div>
                    </td>
                    {STEPS.map(s => (
                      <td key={s.key} className="px-3 py-3 text-center">
                        {s.key === 'audit_done' && !job.audit_required ? (
                          <span className="text-gray-300 text-xs">N/A</span>
                        ) : (
                          <button
                            onClick={() => toggle(job, s.key)}
                            disabled={updateMut.isPending}
                            className="p-1 rounded hover:bg-gray-100"
                          >
                            {job[s.key] ? (
                              <CheckSquare className="w-5 h-5 text-green-500" />
                            ) : (
                              <Square className="w-5 h-5 text-gray-300" />
                            )}
                          </button>
                        )}
                      </td>
                    ))}
                    <td className="px-3 py-3 text-center">
                      {job.audit_required ? (
                        <span className="badge-yellow">ต้องตรวจสอบ</span>
                      ) : (
                        <span className="badge-gray">ไม่ต้องตรวจ</span>
                      )}
                    </td>
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
    </div>
  )
}
