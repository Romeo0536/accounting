import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, getPendingJobs, getUpcomingDeadlines, getUnpaidInvoices } from '../api'
import { Users, ClipboardList, AlertCircle, Receipt, TrendingUp, CheckCircle } from 'lucide-react'
import { MONTH_NAMES_TH } from '../types'
import { Link } from 'react-router-dom'

function formatMoney(n: number) {
  return n.toLocaleString('th-TH', { minimumFractionDigits: 2 })
}

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getDashboardStats })
  const { data: pendingJobs = [] } = useQuery({ queryKey: ['pending-jobs'], queryFn: getPendingJobs })
  const { data: deadlines = [] } = useQuery({ queryKey: ['deadlines'], queryFn: getUpcomingDeadlines })
  const { data: unpaidInv = [] } = useQuery({ queryKey: ['unpaid-invoices'], queryFn: getUnpaidInvoices })

  const month = stats?.current_month || new Date().getMonth() + 1
  const year = stats?.current_year || new Date().getFullYear()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">หน้าหลัก</h1>
        <p className="text-gray-500 text-sm mt-1">
          งานประจำเดือน{MONTH_NAMES_TH[month]} {year + 543}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">ลูกค้าทั้งหมด</div>
              <div className="text-3xl font-bold text-gray-900 mt-1">{stats?.total_clients ?? 0}</div>
              <div className="text-xs text-green-600 mt-1">ใช้งาน {stats?.active_clients ?? 0} ราย</div>
            </div>
            <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-indigo-600" />
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">งานค้างอยู่เดือนนี้</div>
              <div className="text-3xl font-bold text-orange-600 mt-1">{stats?.pending_monthly_jobs ?? 0}</div>
              <div className="text-xs text-green-600 mt-1">เสร็จ {stats?.completed_monthly_jobs ?? 0} งาน</div>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
              <ClipboardList className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">ใบแจ้งหนี้ค้างชำระ</div>
              <div className="text-3xl font-bold text-red-600 mt-1">{stats?.unpaid_invoices ?? 0}</div>
              <div className="text-xs text-red-500 mt-1">฿{formatMoney(stats?.unpaid_amount ?? 0)}</div>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <Receipt className="w-6 h-6 text-red-600" />
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">รายรับเดือนนี้</div>
              <div className="text-2xl font-bold text-green-600 mt-1">฿{formatMoney(stats?.this_month_income ?? 0)}</div>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Jobs */}
        <div className="card">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">งานค้างเดือนนี้</h2>
            <Link to="/monthly-jobs" className="text-indigo-600 text-sm hover:underline">ดูทั้งหมด</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {pendingJobs.length === 0 && (
              <div className="p-8 text-center text-gray-400">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-400" />
                งานเดือนนี้เสร็จหมดแล้ว
              </div>
            )}
            {pendingJobs.slice(0, 8).map((job: any) => (
              <div key={job.id} className="p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{job.client_name}</div>
                  <div className="text-xs text-gray-400">{job.client_code}</div>
                </div>
                <div className="flex gap-1">
                  {[
                    { key: 'documents_received', label: 'เอกสาร' },
                    { key: 'bookkeeping_done', label: 'บัญชี' },
                    { key: 'vat_filed', label: 'VAT' },
                    { key: 'wht_filed', label: 'WHT' },
                    { key: 'financial_statement_done', label: 'งบ' },
                  ].map(({ key, label }) => (
                    <span
                      key={key}
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        job[key] ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'
                      }`}
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upcoming Deadlines */}
        <div className="card">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">ภาษีที่ต้องยื่นเร็วๆ นี้</h2>
            <Link to="/tax-calendar" className="text-indigo-600 text-sm hover:underline">ดูทั้งหมด</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {deadlines.length === 0 && (
              <div className="p-8 text-center text-gray-400">
                <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                ไม่มีภาษีที่ต้องยื่นในขณะนี้
              </div>
            )}
            {deadlines.slice(0, 8).map((d: any) => {
              const dueDate = new Date(d.due_date)
              const today = new Date()
              const daysLeft = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
              return (
                <div key={d.id} className="p-3 flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{d.client_name}</div>
                    <div className="text-xs text-gray-500">{d.filing_type} · {MONTH_NAMES_TH[d.month]} {d.year + 543}</div>
                  </div>
                  <div className={`text-xs font-semibold px-2 py-1 rounded-full ${
                    daysLeft <= 3 ? 'bg-red-100 text-red-700' :
                    daysLeft <= 7 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {daysLeft <= 0 ? 'เกินกำหนด' : `อีก ${daysLeft} วัน`}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Unpaid Invoices */}
      {unpaidInv.length > 0 && (
        <div className="card">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">ใบแจ้งหนี้ค้างชำระ</h2>
            <Link to="/invoices" className="text-indigo-600 text-sm hover:underline">ดูทั้งหมด</Link>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>เลขที่</th>
                  <th>ลูกค้า</th>
                  <th>ยอด</th>
                  <th>ครบกำหนด</th>
                  <th>สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {unpaidInv.map((inv: any) => (
                  <tr key={inv.id}>
                    <td className="font-mono text-xs">{inv.invoice_number}</td>
                    <td>{inv.client_name}</td>
                    <td className="text-right font-medium">฿{formatMoney(inv.total)}</td>
                    <td className="text-sm text-gray-500">{inv.due_date}</td>
                    <td>
                      <span className={inv.status === 'overdue' ? 'badge-red' : 'badge-blue'}>
                        {inv.status === 'overdue' ? 'เกินกำหนด' : 'รอชำระ'}
                      </span>
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
