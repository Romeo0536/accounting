import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, RefreshCw, CheckCircle2, XCircle, Clock, Zap, Calendar, FileText, Receipt } from 'lucide-react'
import { MONTH_NAMES_TH } from '../types'

async function apiPost(path: string, params?: Record<string, number>) {
  const url = new URL(`/api/automation/${path}`, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  const res = await fetch(url.toString(), { method: 'POST' })
  return res.json()
}

async function fetchLogs() {
  const res = await fetch('/api/automation/logs?limit=100')
  return res.json()
}

async function fetchSchedule() {
  const res = await fetch('/api/automation/schedule')
  return res.json()
}

interface RunResult {
  success: boolean
  result?: any
  detail?: string
}

interface TaskDef {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  color: string
  action: (month: number, year: number) => Promise<RunResult>
  needsPeriod: boolean
}

export default function Automation() {
  const qc = useQueryClient()
  const today = new Date()
  const [selMonth, setSelMonth] = useState(today.getMonth() + 1)
  const [selYear, setSelYear] = useState(today.getFullYear())
  const [runResults, setRunResults] = useState<Record<string, RunResult | null>>({})
  const [running, setRunning] = useState<Record<string, boolean>>({})

  const { data: logs = [] } = useQuery({ queryKey: ['auto-logs'], queryFn: fetchLogs, refetchInterval: 10000 })
  const { data: schedule = [] } = useQuery({ queryKey: ['auto-schedule'], queryFn: fetchSchedule })

  const TASKS: TaskDef[] = [
    {
      id: 'monthly-setup',
      title: 'ตั้งต้นเดือนใหม่ (ครบชุด)',
      description: 'สร้างงานรายเดือน + รายการภาษี + ใบแจ้งหนี้ สำหรับลูกค้าทุกรายพร้อมกัน',
      icon: <Zap className="w-5 h-5" />,
      color: 'bg-indigo-600',
      action: (m, y) => apiPost('run/monthly-setup', { month: m, year: y }),
      needsPeriod: true,
    },
    {
      id: 'monthly-jobs',
      title: 'สร้างงานรายเดือน',
      description: 'สร้าง checklist งานบัญชีสำหรับลูกค้า active ทุกราย',
      icon: <CheckCircle2 className="w-5 h-5" />,
      color: 'bg-blue-600',
      action: (m, y) => apiPost('run/monthly-jobs', { month: m, year: y }),
      needsPeriod: true,
    },
    {
      id: 'tax-deadlines',
      title: 'สร้างรายการภาษีพร้อมกำหนดส่ง',
      description: 'สร้างรายการ ภพ.30 / ภงด.1/3/53 / ประกันสังคม ตามเงื่อนไขของแต่ละกิจการ',
      icon: <Calendar className="w-5 h-5" />,
      color: 'bg-purple-600',
      action: (m, y) => apiPost('run/tax-deadlines', { month: m, year: y }),
      needsPeriod: true,
    },
    {
      id: 'invoices',
      title: 'ออกใบแจ้งหนี้รายเดือน',
      description: 'ออกใบแจ้งหนี้ค่าบริการบัญชีสำหรับลูกค้าที่มีค่าบริการรายเดือน',
      icon: <Receipt className="w-5 h-5" />,
      color: 'bg-green-600',
      action: (m, y) => apiPost('run/invoices', { month: m, year: y }),
      needsPeriod: true,
    },
    {
      id: 'mark-overdue',
      title: 'ตรวจสอบ Overdue',
      description: 'ตรวจสอบภาษีและใบแจ้งหนี้ที่เกินกำหนด และอัพเดตสถานะ overdue',
      icon: <XCircle className="w-5 h-5" />,
      color: 'bg-red-600',
      action: () => apiPost('run/mark-overdue'),
      needsPeriod: false,
    },
  ]

  const runTask = async (task: TaskDef) => {
    setRunning(r => ({ ...r, [task.id]: true }))
    setRunResults(r => ({ ...r, [task.id]: null }))
    try {
      const res = await task.action(selMonth, selYear)
      setRunResults(r => ({ ...r, [task.id]: res }))
      qc.invalidateQueries({ queryKey: ['auto-logs'] })
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] })
      qc.invalidateQueries({ queryKey: ['monthly-jobs-all'] })
      qc.invalidateQueries({ queryKey: ['tax-filings'] })
      qc.invalidateQueries({ queryKey: ['invoices-all'] })
    } catch {
      setRunResults(r => ({ ...r, [task.id]: { success: false, detail: 'เกิดข้อผิดพลาด' } }))
    } finally {
      setRunning(r => ({ ...r, [task.id]: false }))
    }
  }

  const formatResult = (result: any) => {
    if (!result) return null
    const r = result.result || result
    const parts: string[] = []
    if (r.created !== undefined) parts.push(`สร้าง ${r.created} รายการ`)
    if (r.skipped !== undefined) parts.push(`ข้าม ${r.skipped} รายการ`)
    if (r.tax_overdue !== undefined) parts.push(`ภาษีเกินกำหนด ${r.tax_overdue} รายการ`)
    if (r.invoice_overdue !== undefined) parts.push(`ใบแจ้งหนี้เกินกำหนด ${r.invoice_overdue} ใบ`)
    if (r.jobs) parts.push(`งาน ${r.jobs.created} / ภาษี ${r.tax_deadlines?.created} / ใบแจ้งหนี้ ${r.invoices?.created}`)
    return parts.join(', ')
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">ระบบ Automation</h1>
        <p className="text-gray-500 text-sm mt-1">จัดการงานอัตโนมัติและกดรันด้วยตัวเอง</p>
      </div>

      {/* Period selector */}
      <div className="card p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Calendar className="w-4 h-4 text-indigo-600" />
          เลือกเดือน/ปีสำหรับรันงาน:
        </div>
        <select className="input w-auto" value={selMonth} onChange={e => setSelMonth(+e.target.value)}>
          {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
        </select>
        <input className="input w-28" type="number" value={selYear} onChange={e => setSelYear(+e.target.value)} />
        <span className="text-sm text-gray-500 bg-indigo-50 px-3 py-1 rounded-full">
          เดือน {MONTH_NAMES_TH[selMonth]} {selYear + 543}
        </span>
      </div>

      {/* Task Cards */}
      <div>
        <h2 className="text-base font-semibold text-gray-700 mb-3">รันด้วยตัวเอง (Manual Trigger)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TASKS.map(task => {
            const res = runResults[task.id]
            const isRunning = running[task.id]
            return (
              <div key={task.id} className="card p-5">
                <div className="flex items-start gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 ${task.color}`}>
                    {task.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-gray-900">{task.title}</div>
                    <div className="text-sm text-gray-500 mt-0.5">{task.description}</div>
                    {task.needsPeriod && (
                      <div className="text-xs text-indigo-600 mt-1">
                        เดือน {MONTH_NAMES_TH[selMonth]} {selYear + 543}
                      </div>
                    )}
                  </div>
                </div>

                {/* Result */}
                {res && (
                  <div className={`mt-3 p-3 rounded-lg text-sm ${
                    res.success ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
                  }`}>
                    {res.success ? (
                      <div className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{formatResult(res) || 'สำเร็จ'}</span>
                      </div>
                    ) : (
                      <div className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                        <span>{res.detail || 'เกิดข้อผิดพลาด'}</span>
                      </div>
                    )}
                  </div>
                )}

                <button
                  onClick={() => runTask(task)}
                  disabled={isRunning}
                  className={`mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors ${task.color} hover:opacity-90 disabled:opacity-50`}
                >
                  {isRunning ? (
                    <><RefreshCw className="w-4 h-4 animate-spin" /> กำลังรัน...</>
                  ) : (
                    <><Play className="w-4 h-4" /> รันตอนนี้</>
                  )}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Scheduled Jobs */}
      <div>
        <h2 className="text-base font-semibold text-gray-700 mb-3">ตารางงานอัตโนมัติ (Scheduled)</h2>
        <div className="space-y-3">
          {schedule.map((job: any) => (
            <div key={job.id} className="card p-4 flex items-start gap-4">
              <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5 text-gray-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-semibold text-gray-900">{job.name}</span>
                  <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    {job.schedule}
                  </span>
                  <span className="badge-green">เปิดใช้งาน</span>
                </div>
                <div className="text-sm text-gray-500 mt-1">{job.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Automation Logs */}
      <div>
        <h2 className="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4" /> ประวัติการรัน
        </h2>
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">เวลา</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">งาน</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">ประเภท</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">สถานะ</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">ผลลัพธ์</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      ยังไม่มีประวัติการรัน
                    </td>
                  </tr>
                )}
                {logs.map((log: any) => (
                  <tr key={log.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {log.created_at ? new Date(log.created_at).toLocaleString('th-TH') : '-'}
                    </td>
                    <td className="px-4 py-3 font-medium">{log.task_name}</td>
                    <td className="px-4 py-3">
                      <span className={log.trigger === 'manual' ? 'badge-blue' : 'badge-gray'}>
                        {log.trigger === 'manual' ? '🖐 Manual' : '⏰ Auto'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {log.status === 'success' ? (
                        <span className="badge-green">✓ สำเร็จ</span>
                      ) : log.status === 'error' ? (
                        <span className="badge-red">✗ Error</span>
                      ) : (
                        <span className="badge-yellow">⚠ Warning</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                      {log.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
