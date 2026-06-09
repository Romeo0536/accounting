import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CheckCircle, Trash2 } from 'lucide-react'
import { getInvoices, createInvoice, markInvoicePaid, deleteInvoice, getClients } from '../api'
import type { Invoice, Client } from '../types'
import { MONTH_NAMES_TH } from '../types'
import StatusBadge from '../components/StatusBadge'

function formatMoney(n: number) {
  return n.toLocaleString('th-TH', { minimumFractionDigits: 2 })
}

export default function Invoices() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState<any>({
    client_id: '',
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: '',
    service_month: new Date().getMonth() + 1,
    service_year: new Date().getFullYear(),
    notes: '',
    items: [{ description: 'ค่าบริการบัญชีประจำเดือน', quantity: 1, unit_price: 0, amount: 0 }],
  })

  const { data: invoices = [] } = useQuery({
    queryKey: ['invoices-all', statusFilter],
    queryFn: () => getInvoices({ status: statusFilter || undefined }),
  })
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => getClients() })

  const createMut = useMutation({
    mutationFn: createInvoice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices-all'] }); setShowModal(false) },
  })
  const paidMut = useMutation({
    mutationFn: (id: number) => markInvoicePaid(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices-all'] }),
  })
  const deleteMut = useMutation({
    mutationFn: deleteInvoice,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices-all'] }),
  })

  const subtotal = form.items.reduce((s: number, item: any) => s + item.amount, 0)
  const vatAmount = Math.round(subtotal * 7 / 100 * 100) / 100
  const total = subtotal + vatAmount

  const updateItem = (idx: number, field: string, value: any) => {
    setForm((f: any) => {
      const items = [...f.items]
      items[idx] = { ...items[idx], [field]: value }
      if (field === 'quantity' || field === 'unit_price') {
        items[idx].amount = items[idx].quantity * items[idx].unit_price
      }
      return { ...f, items }
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMut.mutate({ ...form, client_id: +form.client_id, subtotal, vat_amount: vatAmount, total })
  }

  const totalUnpaid = invoices
    .filter((inv: Invoice) => ['sent', 'overdue'].includes(inv.status))
    .reduce((s: number, inv: Invoice) => s + inv.total, 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">ใบแจ้งหนี้</h1>
          <p className="text-gray-500 text-sm mt-1">ค้างชำระ ฿{formatMoney(totalUnpaid)}</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4" /> ออกใบแจ้งหนี้
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {[
          { value: '', label: 'ทั้งหมด' },
          { value: 'draft', label: 'ร่าง' },
          { value: 'sent', label: 'รอชำระ' },
          { value: 'paid', label: 'ชำระแล้ว' },
          { value: 'overdue', label: 'เกินกำหนด' },
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === value ? 'bg-indigo-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {label} {value === '' && `(${invoices.length})`}
          </button>
        ))}
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>เลขที่ใบแจ้งหนี้</th>
              <th>ลูกค้า</th>
              <th>ค่าบริการเดือน</th>
              <th>วันที่ออก</th>
              <th>ครบกำหนด</th>
              <th className="text-right">ยอดรวม</th>
              <th>สถานะ</th>
              <th>วันที่ชำระ</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv: Invoice) => (
              <tr key={inv.id}>
                <td className="font-mono text-xs">{inv.invoice_number}</td>
                <td>
                  <div className="font-medium">{inv.client?.name}</div>
                  <div className="text-xs text-gray-400">{inv.client?.code}</div>
                </td>
                <td className="text-sm">{inv.service_month ? `${MONTH_NAMES_TH[inv.service_month]} ${inv.service_year}` : '-'}</td>
                <td>{inv.invoice_date}</td>
                <td>{inv.due_date || '-'}</td>
                <td className="text-right font-semibold">฿{formatMoney(inv.total)}</td>
                <td><StatusBadge status={inv.status} /></td>
                <td className="text-sm text-gray-500">{inv.paid_date || '-'}</td>
                <td>
                  <div className="flex items-center gap-2">
                    {['draft', 'sent', 'overdue'].includes(inv.status) && (
                      <button
                        onClick={() => paidMut.mutate(inv.id)}
                        className="text-green-600 hover:text-green-700 text-xs flex items-center gap-1"
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => { if (confirm('ลบใบแจ้งหนี้นี้?')) deleteMut.mutate(inv.id) }}
                      className="text-red-400 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีใบแจ้งหนี้</div>}
      </div>

      {/* Create Invoice Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">ออกใบแจ้งหนี้</h3></div>
            <form className="p-5 space-y-4" onSubmit={handleSubmit}>
              <div className="form-grid-2">
                <div>
                  <label className="label">ลูกค้า *</label>
                  <select className="input" required value={form.client_id}
                    onChange={e => {
                      const client = clients.find((c: Client) => c.id === +e.target.value)
                      setForm((f: any) => ({
                        ...f,
                        client_id: e.target.value,
                        items: [{ description: 'ค่าบริการบัญชีประจำเดือน', quantity: 1, unit_price: client?.monthly_fee || 0, amount: client?.monthly_fee || 0 }],
                      }))
                    }}>
                    <option value="">-- เลือกลูกค้า --</option>
                    {clients.map((c: Client) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">วันที่ออกใบแจ้งหนี้</label>
                  <input className="input" type="date" value={form.invoice_date} onChange={e => setForm((f: any) => ({ ...f, invoice_date: e.target.value }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">ครบกำหนดชำระ</label>
                  <input className="input" type="date" value={form.due_date} onChange={e => setForm((f: any) => ({ ...f, due_date: e.target.value }))} />
                </div>
                <div className="form-grid-2">
                  <div>
                    <label className="label">เดือน</label>
                    <select className="input" value={form.service_month} onChange={e => setForm((f: any) => ({ ...f, service_month: +e.target.value }))}>
                      {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">ปี</label>
                    <input className="input" type="number" value={form.service_year} onChange={e => setForm((f: any) => ({ ...f, service_year: +e.target.value }))} />
                  </div>
                </div>
              </div>

              {/* Items */}
              <div>
                <label className="label">รายการ</label>
                <div className="space-y-2">
                  {form.items.map((item: any, idx: number) => (
                    <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                      <input className="input col-span-5" placeholder="รายการ" value={item.description}
                        onChange={e => updateItem(idx, 'description', e.target.value)} />
                      <input className="input col-span-2" type="number" placeholder="จำนวน" value={item.quantity}
                        onChange={e => updateItem(idx, 'quantity', +e.target.value)} />
                      <input className="input col-span-2" type="number" placeholder="ราคา/หน่วย" value={item.unit_price}
                        onChange={e => updateItem(idx, 'unit_price', +e.target.value)} />
                      <div className="col-span-2 text-right font-medium text-sm">฿{formatMoney(item.amount)}</div>
                      <button type="button" className="col-span-1 text-red-400 hover:text-red-600"
                        onClick={() => setForm((f: any) => ({ ...f, items: f.items.filter((_: any, i: number) => i !== idx) }))}>
                        ×
                      </button>
                    </div>
                  ))}
                  <button type="button" className="text-indigo-600 text-sm hover:underline"
                    onClick={() => setForm((f: any) => ({ ...f, items: [...f.items, { description: '', quantity: 1, unit_price: 0, amount: 0 }] }))}>
                    + เพิ่มรายการ
                  </button>
                </div>
              </div>

              {/* Summary */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
                <div className="flex justify-between"><span>ยอดก่อน VAT:</span><span>฿{formatMoney(subtotal)}</span></div>
                <div className="flex justify-between"><span>VAT 7%:</span><span>฿{formatMoney(vatAmount)}</span></div>
                <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-2">
                  <span>รวมทั้งสิ้น:</span><span className="text-indigo-600">฿{formatMoney(total)}</span>
                </div>
              </div>

              <div>
                <label className="label">หมายเหตุ</label>
                <textarea className="input h-16" value={form.notes} onChange={e => setForm((f: any) => ({ ...f, notes: e.target.value }))} />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary" disabled={createMut.isPending}>
                  {createMut.isPending ? 'กำลังออก...' : 'ออกใบแจ้งหนี้'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
