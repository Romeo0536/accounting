import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, Check, AlertCircle, TrendingUp } from 'lucide-react'
import api from '../api'

interface Expense {
  id: number
  merchant_name: string
  amount: number
  category: string
  receipt_date: string | null
  receipt_time: string
  verified: boolean
  created_at: string
}

interface ExpenseResponse {
  expenses: Expense[]
  total: number
  count: number
  period_days: number
}

async function getExpenses(): Promise<ExpenseResponse> {
  const res = await api.get('/expenses/')
  return res.data
}

async function getSummary() {
  const res = await api.get('/expenses/summary')
  return res.data
}

async function getUnverified() {
  const res = await api.get('/expenses/unverified')
  return res.data
}

export default function ExpenseTracker() {
  const qc = useQueryClient()
  const [selectedDays, setSelectedDays] = useState(30)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editAmount, setEditAmount] = useState<string>('')
  const [editCategory, setEditCategory] = useState<string>('')

  const { data: expenses } = useQuery({
    queryKey: ['expenses'],
    queryFn: getExpenses,
    refetchInterval: 10000,
  })
  const { data: summary } = useQuery({ queryKey: ['expense-summary'], queryFn: getSummary })
  const { data: unverified } = useQuery({ queryKey: ['unverified'], queryFn: getUnverified, refetchInterval: 5000 })

  const verify = useMutation({
    mutationFn: (exp: { id: number; amount?: number; category?: string }) =>
      api.post(`/expenses/${exp.id}/verify`, { amount: exp.amount, category: exp.category }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['unverified'] }); setEditingId(null) },
  })

  const reject = useMutation({
    mutationFn: (id: number) => api.post(`/expenses/${id}/reject`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['unverified'] }) },
  })

  const handleVerify = (e: Expense) => {
    verify.mutate({
      id: e.id,
      amount: editAmount ? parseFloat(editAmount) : e.amount,
      category: editCategory || e.category,
    })
  }

  const categories = ['อาหาร', 'เดินทาง', 'สำนักงาน', 'โทรศัพท์', 'อื่น']

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-orange-600" /> Expense Tracker
        </h1>
        <p className="text-gray-500 text-sm mt-1">ติดตามค่าใช้จ่าย — ส่งสลิป → บอทอ่าน OCR → ยืนยันข้อมูล</p>
      </div>

      {/* Unverified items */}
      {(unverified?.length || 0) > 0 && (
        <div className="card p-5 border-amber-200 bg-amber-50">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <h2 className="font-semibold text-amber-900">รอการยืนยัน ({unverified?.length || 0})</h2>
          </div>
          <div className="space-y-3">
            {unverified?.map((e: any) => (
              <div key={e.id} className="bg-white p-4 rounded-lg border border-amber-200">
                {editingId === e.id ? (
                  <div className="space-y-3">
                    <div>
                      <label className="label">ร้าน</label>
                      <input className="input" defaultValue={e.merchant_name} disabled />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="label">จำนวนเงิน</label>
                        <input className="input" type="number" defaultValue={e.amount}
                          onChange={e => setEditAmount(e.target.value)} />
                      </div>
                      <div>
                        <label className="label">หมวดหมู่</label>
                        <select className="input" defaultValue={e.category} onChange={e => setEditCategory(e.target.value)}>
                          {categories.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => handleVerify(e)} className="btn-success flex-1 flex items-center justify-center gap-1">
                        <Check className="w-4 h-4" /> ยืนยัน
                      </button>
                      <button onClick={() => setEditingId(null)} className="btn-secondary flex-1">ยกเลิก</button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="flex justify-between mb-2">
                      <div className="font-medium">{e.merchant_name || '-'}</div>
                      <div className="text-lg font-bold text-orange-600">{e.amount?.toLocaleString()} บาท</div>
                    </div>
                    <div className="text-xs text-gray-500 mb-3">
                      ความแม่นยำ OCR: {e.ocr_confidence?.toFixed(0)}%
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => { setEditingId(e.id); setEditAmount(''); setEditCategory('') }}
                        className="btn-primary flex-1 flex items-center justify-center gap-1">
                        <Check className="w-4 h-4" /> ยืนยัน
                      </button>
                      <button onClick={() => reject.mutate(e.id)}
                        className="btn-danger flex items-center justify-center gap-1">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div className="card p-5">
          <h2 className="font-semibold mb-4">สรุปตามหมวดหมู่</h2>
          <div className="space-y-2">
            {Object.entries(summary.by_category || {}).map(([cat, data]: any) => (
              <div key={cat} className="flex justify-between items-center p-3 rounded-lg bg-gray-50">
                <div>
                  <div className="font-medium">{cat}</div>
                  <div className="text-xs text-gray-500">{data.count} รายการ</div>
                </div>
                <div className="text-lg font-bold text-orange-600">{data.total?.toLocaleString()} บาท</div>
              </div>
            ))}
            <div className="flex justify-between items-center p-3 rounded-lg bg-orange-50 border border-orange-200 mt-4">
              <div className="font-semibold">ยอดรวม</div>
              <div className="text-2xl font-bold text-orange-600">{summary.total?.toLocaleString()} บาท</div>
            </div>
          </div>
        </div>
      )}

      {/* Expense list */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold">ประวัติรายการ</h2>
          <select className="input w-auto" value={selectedDays} onChange={e => setSelectedDays(+e.target.value)}>
            <option value={7}>7 วัน</option>
            <option value={30}>30 วัน</option>
            <option value={90}>90 วัน</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">วันเวลา</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">ร้าน</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">หมวดหมู่</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">จำนวนเงิน</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500">สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {(expenses?.expenses || []).length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    ยังไม่มีรายการค่าใช้จ่าย
                  </td>
                </tr>
              )}
              {(expenses?.expenses || []).map((e: Expense) => (
                <tr key={e.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                    {e.created_at ? new Date(e.created_at).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' }) : '-'}
                  </td>
                  <td className="px-4 py-3 font-medium">{e.merchant_name || '-'}</td>
                  <td className="px-4 py-3 text-sm">{e.category || '-'}</td>
                  <td className="px-4 py-3 text-right font-semibold text-orange-600">{e.amount?.toLocaleString()} บาท</td>
                  <td className="px-4 py-3 text-center">
                    {e.verified ? (
                      <span className="badge-green">✓ ยืนยัน</span>
                    ) : (
                      <span className="badge-yellow">⏳ รอดำเนินการ</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {expenses?.count && (
          <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-500 text-center">
            {expenses.count} รายการ | ยอดรวม {expenses.total?.toLocaleString()} บาท
          </div>
        )}
      </div>
    </div>
  )
}
