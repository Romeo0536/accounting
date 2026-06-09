import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Search, Building2, Phone, Mail, ChevronRight } from 'lucide-react'
import { getClients, createClient, getStaff } from '../api'
import type { Client } from '../types'
import { BUSINESS_TYPES } from '../types'
import StatusBadge from '../components/StatusBadge'

const INITIAL_FORM = {
  name: '', tax_id: '', business_type: 'บริษัทจำกัด', address: '', phone: '', email: '',
  contact_person: '', service_package: '', monthly_fee: 0, annual_fee: 0,
  vat_registered: false, has_employees: false, fiscal_year_end: 12,
  start_date: '', status: 'active', notes: '', assigned_staff_id: undefined as number | undefined,
}

export default function Clients() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(INITIAL_FORM)

  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => getClients() })
  const { data: staff = [] } = useQuery({ queryKey: ['staff'], queryFn: getStaff })

  const createMut = useMutation({
    mutationFn: createClient,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['clients'] }); setShowModal(false); setForm(INITIAL_FORM) },
  })

  const filtered = clients.filter((c: Client) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.code.toLowerCase().includes(search.toLowerCase()) ||
    (c.tax_id || '').includes(search)
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMut.mutate({ ...form, assigned_staff_id: form.assigned_staff_id || undefined })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">ลูกค้า</h1>
          <p className="text-gray-500 text-sm mt-1">ทั้งหมด {clients.length} ราย</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4" /> เพิ่มลูกค้า
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          className="input pl-10"
          placeholder="ค้นหาชื่อ รหัส หรือเลขที่ผู้เสียภาษี..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Client Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((client: Client) => (
          <Link key={client.id} to={`/clients/${client.id}`} className="card p-4 hover:shadow-md transition-shadow block">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">{client.code}</span>
                  <StatusBadge status={client.status} />
                </div>
                <div className="font-semibold text-gray-900 truncate">{client.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{client.business_type}</div>
              </div>
              <ChevronRight className="w-4 h-4 text-gray-400 mt-1 shrink-0" />
            </div>
            <div className="mt-3 space-y-1">
              {client.phone && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Phone className="w-3 h-3" />{client.phone}
                </div>
              )}
              {client.email && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Mail className="w-3 h-3" />{client.email}
                </div>
              )}
            </div>
            <div className="mt-3 flex gap-3 text-xs">
              {client.vat_registered && <span className="badge-blue">จด VAT</span>}
              {client.has_employees && <span className="badge-gray">มีพนักงาน</span>}
              {client.monthly_fee > 0 && (
                <span className="text-gray-500">฿{client.monthly_fee.toLocaleString()}/เดือน</span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <div>ไม่พบลูกค้า</div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold">เพิ่มลูกค้าใหม่</h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="form-grid-2">
                <div>
                  <label className="label">ชื่อกิจการ *</label>
                  <input className="input" required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">เลขที่ผู้เสียภาษี</label>
                  <input className="input" value={form.tax_id}
                    onChange={e => setForm(f => ({ ...f, tax_id: e.target.value }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">ประเภทธุรกิจ</label>
                  <select className="input" value={form.business_type}
                    onChange={e => setForm(f => ({ ...f, business_type: e.target.value }))}>
                    {BUSINESS_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">ผู้ดูแล</label>
                  <select className="input" value={form.assigned_staff_id || ''}
                    onChange={e => setForm(f => ({ ...f, assigned_staff_id: e.target.value ? +e.target.value : undefined }))}>
                    <option value="">-- เลือกพนักงาน --</option>
                    {staff.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">เบอร์โทรศัพท์</label>
                  <input className="input" value={form.phone}
                    onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
                </div>
                <div>
                  <label className="label">อีเมล</label>
                  <input className="input" type="email" value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">ค่าบริการรายเดือน (บาท)</label>
                  <input className="input" type="number" value={form.monthly_fee}
                    onChange={e => setForm(f => ({ ...f, monthly_fee: +e.target.value }))} />
                </div>
                <div>
                  <label className="label">ค่าบริการประจำปี (บาท)</label>
                  <input className="input" type="number" value={form.annual_fee}
                    onChange={e => setForm(f => ({ ...f, annual_fee: +e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">ที่อยู่</label>
                <textarea className="input h-20" value={form.address}
                  onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">ผู้ติดต่อ</label>
                  <input className="input" value={form.contact_person}
                    onChange={e => setForm(f => ({ ...f, contact_person: e.target.value }))} />
                </div>
                <div>
                  <label className="label">วันที่เริ่มให้บริการ</label>
                  <input className="input" type="date" value={form.start_date}
                    onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
                </div>
              </div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.vat_registered}
                    onChange={e => setForm(f => ({ ...f, vat_registered: e.target.checked }))} />
                  <span className="text-sm">จดทะเบียน VAT</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.has_employees}
                    onChange={e => setForm(f => ({ ...f, has_employees: e.target.checked }))} />
                  <span className="text-sm">มีพนักงาน (ประกันสังคม)</span>
                </label>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary" disabled={createMut.isPending}>
                  {createMut.isPending ? 'กำลังบันทึก...' : 'บันทึก'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
