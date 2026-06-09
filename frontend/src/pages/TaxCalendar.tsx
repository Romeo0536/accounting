import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Calendar, CheckCircle } from 'lucide-react'
import { getTaxFilings, createTaxFiling, updateTaxFiling, getClients } from '../api'
import type { TaxFiling, Client } from '../types'
import { MONTH_NAMES_TH } from '../types'

const FILING_TYPES = ['ภพ.30', 'ภงด.1', 'ภงด.3', 'ภงด.53', 'ภงด.50', 'ภงด.51', 'บอจ.5', 'ประกันสังคม']

export default function TaxCalendar() {
  const qc = useQueryClient()
  const today = new Date()
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [year, setYear] = useState(today.getFullYear())
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<any>({ filing_type: 'ภพ.30', month: today.getMonth() + 1, year: today.getFullYear(), due_date: '', status: 'pending', amount: 0, penalty: 0 })

  const { data: filings = [] } = useQuery({
    queryKey: ['tax-filings', month, year],
    queryFn: () => getTaxFilings({ month, year }),
  })
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => getClients() })

  const createMut = useMutation({
    mutationFn: createTaxFiling,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tax-filings'] }); setShowModal(false) },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateTaxFiling(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tax-filings'] }),
  })

  const markFiled = (filing: TaxFiling) => {
    updateMut.mutate({
      id: filing.id,
      data: { status: 'filed', filed_date: today.toISOString().split('T')[0] },
    })
  }

  // Group by filing type
  const grouped = FILING_TYPES.reduce((acc, type) => {
    acc[type] = filings.filter((f: TaxFiling) => f.filing_type === type)
    return acc
  }, {} as Record<string, TaxFiling[]>)

  const pending = filings.filter((f: TaxFiling) => f.status === 'pending').length
  const filed = filings.filter((f: TaxFiling) => f.status === 'filed').length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">ปฏิทินภาษี</h1>
          <p className="text-gray-500 text-sm mt-1">รอยื่น {pending} รายการ · ยื่นแล้ว {filed} รายการ</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-auto" value={month} onChange={e => setMonth(+e.target.value)}>
            {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
          </select>
          <input className="input w-24" type="number" value={year} onChange={e => setYear(+e.target.value)} />
          <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
            <Plus className="w-4 h-4" /> เพิ่มรายการ
          </button>
        </div>
      </div>

      {/* Tax deadline info card */}
      <div className="card p-4 bg-indigo-50 border-indigo-200">
        <div className="flex items-start gap-3">
          <Calendar className="w-5 h-5 text-indigo-600 mt-0.5" />
          <div className="text-sm text-indigo-800">
            <div className="font-semibold mb-1">กำหนดยื่นแบบเดือน {MONTH_NAMES_TH[month]}</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div><span className="font-medium">ภงด.1/3/53:</span> วันที่ 7 (15 e-filing)</div>
              <div><span className="font-medium">ภพ.30:</span> วันที่ 15 (23 e-filing)</div>
              <div><span className="font-medium">ประกันสังคม:</span> วันที่ 15</div>
              <div><span className="font-medium">ภงด.50/51:</span> ภายใน 150 วัน</div>
            </div>
          </div>
        </div>
      </div>

      {filings.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <div>ไม่มีรายการภาษีเดือนนี้</div>
        </div>
      )}

      {/* Grouped by type */}
      {FILING_TYPES.map(type => {
        const items = grouped[type]
        if (!items || items.length === 0) return null
        return (
          <div key={type} className="card overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
              <span className="font-semibold text-sm">{type}</span>
              <span className="text-xs text-gray-500">{items.filter(f => f.status === 'filed').length}/{items.length} ยื่นแล้ว</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>ลูกค้า</th>
                  <th>ครบกำหนด</th>
                  <th className="text-right">ยอดภาษี</th>
                  <th className="text-right">ค่าปรับ</th>
                  <th>อ้างอิง</th>
                  <th>สถานะ</th>
                  <th>วันที่ยื่น</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((f: TaxFiling) => {
                  const dueDate = f.due_date ? new Date(f.due_date) : null
                  const isOverdue = dueDate && dueDate < today && f.status === 'pending'
                  return (
                    <tr key={f.id} className={isOverdue ? 'bg-red-50' : ''}>
                      <td>
                        <div className="font-medium">{f.client?.name}</div>
                        <div className="text-xs text-gray-400">{f.client?.code}</div>
                      </td>
                      <td className={isOverdue ? 'text-red-600 font-medium' : ''}>{f.due_date}</td>
                      <td className="text-right">{f.amount != null ? `฿${f.amount.toLocaleString()}` : '-'}</td>
                      <td className="text-right text-red-500">{f.penalty > 0 ? `฿${f.penalty.toLocaleString()}` : '-'}</td>
                      <td className="font-mono text-xs">{f.reference_number || '-'}</td>
                      <td>
                        {f.status === 'filed' ? (
                          <span className="badge-green">ยื่นแล้ว</span>
                        ) : isOverdue ? (
                          <span className="badge-red">เกินกำหนด</span>
                        ) : (
                          <span className="badge-gray">รอยื่น</span>
                        )}
                      </td>
                      <td className="text-sm text-gray-500">{f.filed_date || '-'}</td>
                      <td>
                        {f.status === 'pending' && (
                          <button
                            onClick={() => markFiled(f)}
                            className="flex items-center gap-1 text-green-600 hover:text-green-700 text-xs font-medium"
                          >
                            <CheckCircle className="w-4 h-4" /> ยื่นแล้ว
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      })}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">เพิ่มรายการภาษี</h3></div>
            <form className="p-5 space-y-3" onSubmit={e => { e.preventDefault(); createMut.mutate(form) }}>
              <div className="form-grid-2">
                <div>
                  <label className="label">ลูกค้า *</label>
                  <select className="input" required value={form.client_id || ''} onChange={e => setForm((f: any) => ({ ...f, client_id: +e.target.value }))}>
                    <option value="">-- เลือกลูกค้า --</option>
                    {clients.map((c: Client) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">ประเภทแบบ</label>
                  <select className="input" value={form.filing_type} onChange={e => setForm((f: any) => ({ ...f, filing_type: e.target.value }))}>
                    {FILING_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">เดือน</label>
                  <select className="input" value={form.month} onChange={e => setForm((f: any) => ({ ...f, month: +e.target.value }))}>
                    {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">ปี (ค.ศ.)</label>
                  <input className="input" type="number" value={form.year} onChange={e => setForm((f: any) => ({ ...f, year: +e.target.value }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">ครบกำหนดวันที่</label>
                  <input className="input" type="date" value={form.due_date} onChange={e => setForm((f: any) => ({ ...f, due_date: e.target.value }))} />
                </div>
                <div>
                  <label className="label">ยอดภาษี (บาท)</label>
                  <input className="input" type="number" step="0.01" value={form.amount} onChange={e => setForm((f: any) => ({ ...f, amount: +e.target.value }))} />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary">บันทึก</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
