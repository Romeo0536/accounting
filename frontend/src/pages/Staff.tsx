import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { getStaff, createStaff, updateStaff, deleteStaff } from '../api'
import type { Staff } from '../types'

const ROLES = ['นักบัญชี', 'ผู้จัดการบัญชี', 'ผู้ตรวจสอบบัญชี', 'ผู้ช่วยบัญชี', 'เจ้าของ/หุ้นส่วน']

export default function StaffPage() {
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Staff | null>(null)
  const [form, setForm] = useState({ name: '', role: '', email: '', phone: '', active: true })

  const { data: staff = [] } = useQuery({ queryKey: ['staff'], queryFn: getStaff })

  const createMut = useMutation({
    mutationFn: createStaff,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['staff'] }); close() },
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateStaff(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['staff'] }); close() },
  })
  const deleteMut = useMutation({
    mutationFn: deleteStaff,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  })

  const close = () => { setShowModal(false); setEditing(null); setForm({ name: '', role: '', email: '', phone: '', active: true }) }

  const openEdit = (s: Staff) => { setEditing(s); setForm({ name: s.name, role: s.role || '', email: s.email || '', phone: s.phone || '', active: s.active }); setShowModal(true) }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editing) updateMut.mutate({ id: editing.id, data: form })
    else createMut.mutate(form)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">พนักงาน</h1>
          <p className="text-gray-500 text-sm mt-1">ทั้งหมด {staff.length} คน</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4" /> เพิ่มพนักงาน
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {staff.map((s: Staff) => (
          <div key={s.id} className="card p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold text-lg mb-3">
                  {s.name.charAt(0)}
                </div>
                <div className="font-semibold">{s.name}</div>
                <div className="text-sm text-gray-500">{s.role || '-'}</div>
              </div>
              <span className={s.active ? 'badge-green' : 'badge-gray'}>{s.active ? 'ใช้งาน' : 'ไม่ใช้'}</span>
            </div>
            <div className="mt-3 space-y-1 text-sm text-gray-500">
              {s.email && <div>📧 {s.email}</div>}
              {s.phone && <div>📞 {s.phone}</div>}
            </div>
            <div className="mt-4 flex gap-2">
              <button className="btn-secondary flex-1 flex items-center justify-center gap-1 text-xs" onClick={() => openEdit(s)}>
                <Edit2 className="w-3 h-3" /> แก้ไข
              </button>
              <button
                className="btn-danger flex items-center justify-center gap-1 text-xs"
                onClick={() => { if (confirm('ลบพนักงานนี้?')) deleteMut.mutate(s.id) }}
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
        {staff.length === 0 && (
          <div className="col-span-3 text-center py-12 text-gray-400">ยังไม่มีพนักงาน</div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={close}>
          <div className="modal max-w-md" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">{editing ? 'แก้ไขพนักงาน' : 'เพิ่มพนักงาน'}</h3></div>
            <form className="p-5 space-y-3" onSubmit={handleSubmit}>
              <div>
                <label className="label">ชื่อ-นามสกุล *</label>
                <input className="input" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="label">ตำแหน่ง</label>
                <select className="input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                  <option value="">-- เลือก --</option>
                  {ROLES.map(r => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="label">อีเมล</label>
                <input className="input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div>
                <label className="label">เบอร์โทรศัพท์</label>
                <input className="input" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.active} onChange={e => setForm(f => ({ ...f, active: e.target.checked }))} />
                <span className="text-sm">ใช้งานอยู่</span>
              </label>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={close}>ยกเลิก</button>
                <button type="submit" className="btn-primary">บันทึก</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
