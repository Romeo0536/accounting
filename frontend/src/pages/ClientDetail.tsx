import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit2, Save, X, Plus, Trash2 } from 'lucide-react'
import {
  getClient, updateClient, getMonthlyJobs, getAnnualJobs,
  getTransactions, getWHTRecords, getDocuments, getInvoices,
  createTransaction, deleteTransaction, createDocument, deleteDocument,
  createWHTRecord, deleteWHTRecord,
} from '../api'
import type { Transaction, WHTRecord, Document } from '../types'
import {
  MONTH_NAMES_TH, INCOME_CATEGORIES, EXPENSE_CATEGORIES,
  DOCUMENT_TYPES, WHT_TYPES, INCOME_TYPES_WHT,
} from '../types'
import StatusBadge from '../components/StatusBadge'

type Tab = 'overview' | 'monthly' | 'annual' | 'transactions' | 'wht' | 'documents' | 'invoices'

function formatMoney(n: number) {
  return n.toLocaleString('th-TH', { minimumFractionDigits: 2 })
}

export default function ClientDetail() {
  const { id } = useParams<{ id: string }>()
  const clientId = Number(id)
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('overview')
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<any>({})
  const [showTxModal, setShowTxModal] = useState(false)
  const [showDocModal, setShowDocModal] = useState(false)
  const [showWHTModal, setShowWHTModal] = useState(false)
  const [txForm, setTxForm] = useState<any>({ transaction_type: 'income', date: new Date().toISOString().split('T')[0], amount: 0, vat_rate: 7, vat_amount: 0, total_amount: 0 })
  const [docForm, setDocForm] = useState<any>({ document_type: 'ใบเสร็จรับเงิน / ใบกำกับภาษี', quantity: 1 })
  const [whtForm, setWhtForm] = useState<any>({ wht_type: 'ภงด.3', direction: 'issued', date: new Date().toISOString().split('T')[0], wht_rate: 3, income_amount: 0, wht_amount: 0 })
  const [filterMonth, setFilterMonth] = useState(new Date().getMonth() + 1)
  const [filterYear, setFilterYear] = useState(new Date().getFullYear())

  const { data: client } = useQuery({ queryKey: ['client', clientId], queryFn: () => getClient(clientId) })
  const { data: monthlyJobs = [] } = useQuery({ queryKey: ['monthly-jobs', clientId], queryFn: () => getMonthlyJobs({ client_id: clientId }) })
  const { data: annualJobs = [] } = useQuery({ queryKey: ['annual-jobs', clientId], queryFn: () => getAnnualJobs({ client_id: clientId }) })
  const { data: transactions = [] } = useQuery({ queryKey: ['transactions', clientId, filterMonth, filterYear], queryFn: () => getTransactions({ client_id: clientId, month: filterMonth, year: filterYear }) })
  const { data: whtRecords = [] } = useQuery({ queryKey: ['wht-records', clientId, filterMonth, filterYear], queryFn: () => getWHTRecords({ client_id: clientId, month: filterMonth, year: filterYear }) })
  const { data: documents = [] } = useQuery({ queryKey: ['documents', clientId], queryFn: () => getDocuments({ client_id: clientId }) })
  const { data: invoices = [] } = useQuery({ queryKey: ['invoices', clientId], queryFn: () => getInvoices({ client_id: clientId }) })

  const updateMut = useMutation({ mutationFn: (d: any) => updateClient(clientId, d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['client', clientId] }); setEditing(false) } })
  const createTxMut = useMutation({ mutationFn: createTransaction, onSuccess: () => { qc.invalidateQueries({ queryKey: ['transactions', clientId] }); setShowTxModal(false) } })
  const deleteTxMut = useMutation({ mutationFn: deleteTransaction, onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions', clientId] }) })
  const createDocMut = useMutation({ mutationFn: createDocument, onSuccess: () => { qc.invalidateQueries({ queryKey: ['documents', clientId] }); setShowDocModal(false) } })
  const deleteDocMut = useMutation({ mutationFn: deleteDocument, onSuccess: () => qc.invalidateQueries({ queryKey: ['documents', clientId] }) })
  const createWHTMut = useMutation({ mutationFn: createWHTRecord, onSuccess: () => { qc.invalidateQueries({ queryKey: ['wht-records', clientId] }); setShowWHTModal(false) } })
  const deleteWHTMut = useMutation({ mutationFn: deleteWHTRecord, onSuccess: () => qc.invalidateQueries({ queryKey: ['wht-records', clientId] }) })

  if (!client) return <div className="p-8 text-center text-gray-400">กำลังโหลด...</div>

  const startEdit = () => { setEditForm({ ...client }); setEditing(true) }

  // Summaries
  const income = transactions.filter((t: Transaction) => t.transaction_type === 'income')
  const expense = transactions.filter((t: Transaction) => t.transaction_type === 'expense')
  const totalIncome = income.reduce((s: number, t: Transaction) => s + t.amount, 0)
  const totalExpense = expense.reduce((s: number, t: Transaction) => s + t.amount, 0)
  const totalVATIn = income.reduce((s: number, t: Transaction) => s + t.vat_amount, 0)  // ภาษีขาย
  const totalVATOut = expense.reduce((s: number, t: Transaction) => s + t.vat_amount, 0) // ภาษีซื้อ

  const computeVAT = (amount: number, rate: number) => Math.round(amount * rate / 100 * 100) / 100

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'ข้อมูลทั่วไป' },
    { key: 'transactions', label: 'รายรับ-รายจ่าย' },
    { key: 'wht', label: 'ภาษีหัก ณ ที่จ่าย' },
    { key: 'monthly', label: 'งานรายเดือน' },
    { key: 'annual', label: 'งานประจำปี' },
    { key: 'documents', label: 'เอกสาร' },
    { key: 'invoices', label: 'ใบแจ้งหนี้' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link to="/clients" className="mt-1 p-1.5 rounded-lg hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <span className="text-sm font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">{client.code}</span>
            <StatusBadge status={client.status} />
            {client.vat_registered && <span className="badge-blue">จด VAT</span>}
          </div>
          <h1 className="text-2xl font-bold mt-1">{client.name}</h1>
          <p className="text-gray-500 text-sm">{client.business_type} · เลขที่ผู้เสียภาษี: {client.tax_id || '-'}</p>
        </div>
        {!editing && (
          <button className="btn-secondary flex items-center gap-2" onClick={startEdit}>
            <Edit2 className="w-4 h-4" /> แก้ไข
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              tab === t.key ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === 'overview' && (
        <div className="card p-6">
          {editing ? (
            <div className="space-y-4">
              <div className="form-grid-2">
                <div><label className="label">ชื่อกิจการ</label><input className="input" value={editForm.name || ''} onChange={e => setEditForm((f: any) => ({ ...f, name: e.target.value }))} /></div>
                <div><label className="label">เลขที่ผู้เสียภาษี</label><input className="input" value={editForm.tax_id || ''} onChange={e => setEditForm((f: any) => ({ ...f, tax_id: e.target.value }))} /></div>
              </div>
              <div className="form-grid-2">
                <div><label className="label">เบอร์โทร</label><input className="input" value={editForm.phone || ''} onChange={e => setEditForm((f: any) => ({ ...f, phone: e.target.value }))} /></div>
                <div><label className="label">อีเมล</label><input className="input" value={editForm.email || ''} onChange={e => setEditForm((f: any) => ({ ...f, email: e.target.value }))} /></div>
              </div>
              <div className="form-grid-2">
                <div><label className="label">ค่าบริการรายเดือน</label><input className="input" type="number" value={editForm.monthly_fee || 0} onChange={e => setEditForm((f: any) => ({ ...f, monthly_fee: +e.target.value }))} /></div>
                <div><label className="label">ค่าบริการประจำปี</label><input className="input" type="number" value={editForm.annual_fee || 0} onChange={e => setEditForm((f: any) => ({ ...f, annual_fee: +e.target.value }))} /></div>
              </div>
              <div><label className="label">ที่อยู่</label><textarea className="input h-20" value={editForm.address || ''} onChange={e => setEditForm((f: any) => ({ ...f, address: e.target.value }))} /></div>
              <div><label className="label">หมายเหตุ</label><textarea className="input h-20" value={editForm.notes || ''} onChange={e => setEditForm((f: any) => ({ ...f, notes: e.target.value }))} /></div>
              <div className="flex justify-end gap-3">
                <button className="btn-secondary flex items-center gap-2" onClick={() => setEditing(false)}><X className="w-4 h-4" /> ยกเลิก</button>
                <button className="btn-primary flex items-center gap-2" onClick={() => updateMut.mutate(editForm)}><Save className="w-4 h-4" /> บันทึก</button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <InfoRow label="เบอร์โทรศัพท์" value={client.phone} />
                <InfoRow label="อีเมล" value={client.email} />
                <InfoRow label="ผู้ติดต่อ" value={client.contact_person} />
                <InfoRow label="ที่อยู่" value={client.address} />
                <InfoRow label="หมายเหตุ" value={client.notes} />
              </div>
              <div className="space-y-3">
                <InfoRow label="ค่าบริการรายเดือน" value={client.monthly_fee ? `฿${client.monthly_fee.toLocaleString()}` : undefined} />
                <InfoRow label="ค่าบริการประจำปี" value={client.annual_fee ? `฿${client.annual_fee.toLocaleString()}` : undefined} />
                <InfoRow label="สิ้นปีบัญชีเดือน" value={MONTH_NAMES_TH[client.fiscal_year_end]} />
                <InfoRow label="วันที่เริ่มให้บริการ" value={client.start_date} />
                <InfoRow label="จดทะเบียน VAT" value={client.vat_registered ? 'ใช่' : 'ไม่'} />
                <InfoRow label="มีพนักงาน" value={client.has_employees ? 'ใช่' : 'ไม่'} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Transactions Tab */}
      {tab === 'transactions' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">
              <select className="input w-auto" value={filterMonth} onChange={e => setFilterMonth(+e.target.value)}>
                {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
              <input className="input w-28" type="number" value={filterYear} onChange={e => setFilterYear(+e.target.value)} />
            </div>
            <button className="btn-primary flex items-center gap-2" onClick={() => setShowTxModal(true)}>
              <Plus className="w-4 h-4" /> เพิ่มรายการ
            </button>
          </div>

          {/* VAT Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'รายรับ', value: totalIncome, color: 'text-green-600' },
              { label: 'รายจ่าย', value: totalExpense, color: 'text-red-500' },
              { label: 'ภาษีขาย', value: totalVATIn, color: 'text-blue-600' },
              { label: 'ภาษีซื้อ', value: totalVATOut, color: 'text-orange-600' },
            ].map(({ label, value, color }) => (
              <div key={label} className="card p-3 text-center">
                <div className="text-xs text-gray-500">{label}</div>
                <div className={`text-lg font-bold ${color}`}>฿{formatMoney(value)}</div>
              </div>
            ))}
          </div>
          <div className="card p-3 text-center">
            <span className="text-sm text-gray-500">VAT สุทธิที่ต้องชำระ: </span>
            <span className={`font-bold ${totalVATIn - totalVATOut >= 0 ? 'text-red-600' : 'text-green-600'}`}>
              ฿{formatMoney(totalVATIn - totalVATOut)}
            </span>
            <span className="text-xs text-gray-400 ml-2">
              ({totalVATIn - totalVATOut >= 0 ? 'ชำระเพิ่ม' : 'ขอคืน'})
            </span>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>วันที่</th><th>ประเภท</th><th>เลขที่เอกสาร</th><th>คู่ค้า</th>
                  <th>คำอธิบาย</th><th className="text-right">มูลค่า</th><th className="text-right">VAT</th><th className="text-right">รวม</th><th></th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx: Transaction) => (
                  <tr key={tx.id}>
                    <td className="text-sm">{tx.date}</td>
                    <td><span className={tx.transaction_type === 'income' ? 'badge-green' : 'badge-red'}>{tx.transaction_type === 'income' ? 'รายรับ' : 'รายจ่าย'}</span></td>
                    <td className="font-mono text-xs">{tx.document_number}</td>
                    <td>{tx.counterparty}</td>
                    <td className="text-sm text-gray-600">{tx.description}</td>
                    <td className="text-right font-mono">{formatMoney(tx.amount)}</td>
                    <td className="text-right font-mono text-blue-600">{formatMoney(tx.vat_amount)}</td>
                    <td className="text-right font-mono font-medium">{formatMoney(tx.total_amount)}</td>
                    <td><button onClick={() => deleteTxMut.mutate(tx.id)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {transactions.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีรายการ</div>}
          </div>
        </div>
      )}

      {/* WHT Tab */}
      {tab === 'wht' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">
              <select className="input w-auto" value={filterMonth} onChange={e => setFilterMonth(+e.target.value)}>
                {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
              </select>
              <input className="input w-28" type="number" value={filterYear} onChange={e => setFilterYear(+e.target.value)} />
            </div>
            <button className="btn-primary flex items-center gap-2" onClick={() => setShowWHTModal(true)}>
              <Plus className="w-4 h-4" /> เพิ่มรายการ WHT
            </button>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>วันที่</th><th>ประเภท</th><th>ทิศทาง</th><th>ชื่อผู้รับ</th>
                  <th>ประเภทเงินได้</th><th className="text-right">เงินได้</th>
                  <th className="text-right">อัตรา%</th><th className="text-right">ภาษีหัก</th><th></th>
                </tr>
              </thead>
              <tbody>
                {whtRecords.map((r: WHTRecord) => (
                  <tr key={r.id}>
                    <td>{r.date}</td>
                    <td><span className="badge-blue">{r.wht_type}</span></td>
                    <td>{r.direction === 'issued' ? '🔴 ออก' : '🟢 รับ'}</td>
                    <td>{r.payee_name}</td>
                    <td className="text-sm">{r.income_type}</td>
                    <td className="text-right font-mono">{formatMoney(r.income_amount)}</td>
                    <td className="text-right">{r.wht_rate}%</td>
                    <td className="text-right font-mono font-medium">{formatMoney(r.wht_amount)}</td>
                    <td><button onClick={() => deleteWHTMut.mutate(r.id)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {whtRecords.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีรายการ</div>}
          </div>
        </div>
      )}

      {/* Monthly Jobs Tab */}
      {tab === 'monthly' && (
        <div className="space-y-3">
          {monthlyJobs.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีข้อมูลงานรายเดือน</div>}
          {monthlyJobs.map((job: any) => (
            <div key={job.id} className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold">{MONTH_NAMES_TH[job.month]} {job.year + 543}</span>
                <StatusBadge status={job.status} />
              </div>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
                {[
                  { key: 'documents_received', label: 'รับเอกสาร', date: job.documents_received_date },
                  { key: 'bookkeeping_done', label: 'บันทึกบัญชี', date: job.bookkeeping_done_date },
                  { key: 'vat_filed', label: 'ยื่น ภพ.30', date: job.vat_filed_date },
                  { key: 'wht_filed', label: 'ยื่น ภงด.', date: job.wht_filed_date },
                  { key: 'sso_filed', label: 'ประกันสังคม', date: job.sso_filed_date },
                  { key: 'financial_statement_done', label: 'จัดทำงบ', date: job.financial_statement_done_date },
                ].map(({ key, label, date }) => (
                  <div key={key} className={`p-2 rounded-lg text-center ${job[key] ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                    <div className={job[key] ? 'text-green-600' : 'text-gray-400'}>{job[key] ? '✓' : '○'}</div>
                    <div className={job[key] ? 'text-green-700 font-medium' : 'text-gray-500'}>{label}</div>
                    {date && <div className="text-gray-400 text-xs mt-0.5">{date}</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Annual Jobs Tab */}
      {tab === 'annual' && (
        <div className="space-y-3">
          {annualJobs.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีข้อมูลงานประจำปี</div>}
          {annualJobs.map((job: any) => (
            <div key={job.id} className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold">ปี {job.year + 543}</span>
                <StatusBadge status={job.status} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                {[
                  { key: 'annual_fs_done', label: 'งบการเงินประจำปี' },
                  { key: 'pnd51_filed', label: 'ยื่น ภงด.51' },
                  { key: 'pnd50_filed', label: 'ยื่น ภงด.50' },
                  { key: 'boj5_filed', label: 'ยื่น บอจ.5' },
                  { key: 'audit_done', label: 'ตรวจสอบบัญชี' },
                ].map(({ key, label }) => (
                  <div key={key} className={`p-2 rounded-lg text-center ${job[key] ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
                    <div className={job[key] ? 'text-green-600 text-lg' : 'text-gray-400 text-lg'}>{job[key] ? '✓' : '○'}</div>
                    <div className={job[key] ? 'text-green-700 font-medium' : 'text-gray-500'}>{label}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Documents Tab */}
      {tab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button className="btn-primary flex items-center gap-2" onClick={() => setShowDocModal(true)}>
              <Plus className="w-4 h-4" /> เพิ่มเอกสาร
            </button>
          </div>
          <div className="table-container">
            <table>
              <thead><tr><th>ประเภทเอกสาร</th><th>เดือน/ปี</th><th>คำอธิบาย</th><th>จำนวน</th><th>วันที่รับ</th><th></th></tr></thead>
              <tbody>
                {documents.map((d: Document) => (
                  <tr key={d.id}>
                    <td>{d.document_type}</td>
                    <td>{d.month ? `${MONTH_NAMES_TH[d.month]} ${d.year}` : ''}</td>
                    <td>{d.description}</td>
                    <td>{d.quantity}</td>
                    <td>{d.received_date}</td>
                    <td><button onClick={() => deleteDocMut.mutate(d.id)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {documents.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีเอกสาร</div>}
          </div>
        </div>
      )}

      {/* Invoices Tab */}
      {tab === 'invoices' && (
        <div className="table-container">
          <table>
            <thead><tr><th>เลขที่</th><th>วันที่</th><th>ค่าบริการเดือน</th><th className="text-right">ยอดรวม</th><th>สถานะ</th></tr></thead>
            <tbody>
              {invoices.map((inv: any) => (
                <tr key={inv.id}>
                  <td className="font-mono text-xs">{inv.invoice_number}</td>
                  <td>{inv.invoice_date}</td>
                  <td>{inv.service_month ? `${MONTH_NAMES_TH[inv.service_month]} ${inv.service_year}` : ''}</td>
                  <td className="text-right font-medium">฿{formatMoney(inv.total)}</td>
                  <td><StatusBadge status={inv.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {invoices.length === 0 && <div className="p-8 text-center text-gray-400">ไม่มีใบแจ้งหนี้</div>}
        </div>
      )}

      {/* Transaction Modal */}
      {showTxModal && (
        <div className="modal-overlay" onClick={() => setShowTxModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">เพิ่มรายการซื้อ/ขาย</h3></div>
            <form className="p-5 space-y-3" onSubmit={e => { e.preventDefault(); createTxMut.mutate({ ...txForm, client_id: clientId }) }}>
              <div className="form-grid-2">
                <div>
                  <label className="label">ประเภท</label>
                  <select className="input" value={txForm.transaction_type} onChange={e => setTxForm((f: any) => ({ ...f, transaction_type: e.target.value }))}>
                    <option value="income">รายรับ (ขาย)</option>
                    <option value="expense">รายจ่าย (ซื้อ)</option>
                  </select>
                </div>
                <div>
                  <label className="label">วันที่</label>
                  <input className="input" type="date" value={txForm.date} onChange={e => setTxForm((f: any) => ({ ...f, date: e.target.value }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">เลขที่เอกสาร</label>
                  <input className="input" value={txForm.document_number || ''} onChange={e => setTxForm((f: any) => ({ ...f, document_number: e.target.value }))} />
                </div>
                <div>
                  <label className="label">คู่ค้า</label>
                  <input className="input" value={txForm.counterparty || ''} onChange={e => setTxForm((f: any) => ({ ...f, counterparty: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="label">หมวดหมู่</label>
                <select className="input" value={txForm.category || ''} onChange={e => setTxForm((f: any) => ({ ...f, category: e.target.value }))}>
                  <option value="">-- เลือก --</option>
                  {(txForm.transaction_type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES).map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="label">คำอธิบาย</label>
                <input className="input" value={txForm.description || ''} onChange={e => setTxForm((f: any) => ({ ...f, description: e.target.value }))} />
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">มูลค่าก่อน VAT (บาท)</label>
                  <input className="input" type="number" step="0.01" value={txForm.amount}
                    onChange={e => {
                      const amt = +e.target.value
                      const vat = computeVAT(amt, txForm.vat_rate)
                      setTxForm((f: any) => ({ ...f, amount: amt, vat_amount: vat, total_amount: amt + vat }))
                    }} />
                </div>
                <div>
                  <label className="label">อัตรา VAT (%)</label>
                  <select className="input" value={txForm.vat_rate}
                    onChange={e => {
                      const rate = +e.target.value
                      const vat = computeVAT(txForm.amount, rate)
                      setTxForm((f: any) => ({ ...f, vat_rate: rate, vat_amount: vat, total_amount: txForm.amount + vat }))
                    }}>
                    <option value={0}>0% (ไม่มี VAT)</option>
                    <option value={7}>7%</option>
                  </select>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                <div className="flex justify-between"><span className="text-gray-500">ภาษีมูลค่าเพิ่ม:</span><span className="font-medium">฿{formatMoney(txForm.vat_amount)}</span></div>
                <div className="flex justify-between"><span className="font-semibold">รวมทั้งสิ้น:</span><span className="font-bold text-indigo-600">฿{formatMoney(txForm.total_amount)}</span></div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowTxModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary">บันทึก</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* WHT Modal */}
      {showWHTModal && (
        <div className="modal-overlay" onClick={() => setShowWHTModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">เพิ่มภาษีหัก ณ ที่จ่าย</h3></div>
            <form className="p-5 space-y-3" onSubmit={e => { e.preventDefault(); createWHTMut.mutate({ ...whtForm, client_id: clientId }) }}>
              <div className="form-grid-2">
                <div>
                  <label className="label">ประเภทแบบ</label>
                  <select className="input" value={whtForm.wht_type} onChange={e => setWhtForm((f: any) => ({ ...f, wht_type: e.target.value }))}>
                    {WHT_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">ทิศทาง</label>
                  <select className="input" value={whtForm.direction} onChange={e => setWhtForm((f: any) => ({ ...f, direction: e.target.value }))}>
                    <option value="issued">ออก (เราหักจากคู่ค้า)</option>
                    <option value="received">รับ (คู่ค้าหักจากเรา)</option>
                  </select>
                </div>
              </div>
              <div className="form-grid-2">
                <div><label className="label">วันที่</label><input className="input" type="date" value={whtForm.date} onChange={e => setWhtForm((f: any) => ({ ...f, date: e.target.value }))} /></div>
                <div><label className="label">ชื่อผู้รับเงิน</label><input className="input" value={whtForm.payee_name || ''} onChange={e => setWhtForm((f: any) => ({ ...f, payee_name: e.target.value }))} /></div>
              </div>
              <div>
                <label className="label">ประเภทเงินได้</label>
                <select className="input" value={whtForm.income_type || ''} onChange={e => setWhtForm((f: any) => ({ ...f, income_type: e.target.value }))}>
                  <option value="">-- เลือก --</option>
                  {INCOME_TYPES_WHT.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">จำนวนเงินได้ (บาท)</label>
                  <input className="input" type="number" step="0.01" value={whtForm.income_amount}
                    onChange={e => {
                      const amt = +e.target.value
                      setWhtForm((f: any) => ({ ...f, income_amount: amt, wht_amount: Math.round(amt * f.wht_rate / 100 * 100) / 100 }))
                    }} />
                </div>
                <div>
                  <label className="label">อัตราภาษีหัก (%)</label>
                  <select className="input" value={whtForm.wht_rate}
                    onChange={e => {
                      const rate = +e.target.value
                      setWhtForm((f: any) => ({ ...f, wht_rate: rate, wht_amount: Math.round(f.income_amount * rate / 100 * 100) / 100 }))
                    }}>
                    {[1, 2, 3, 5, 10, 15].map(r => <option key={r} value={r}>{r}%</option>)}
                  </select>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-sm">
                <div className="flex justify-between"><span className="font-semibold">ภาษีหัก ณ ที่จ่าย:</span><span className="font-bold text-indigo-600">฿{formatMoney(whtForm.wht_amount)}</span></div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowWHTModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary">บันทึก</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document Modal */}
      {showDocModal && (
        <div className="modal-overlay" onClick={() => setShowDocModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b"><h3 className="font-semibold">บันทึกรับเอกสาร</h3></div>
            <form className="p-5 space-y-3" onSubmit={e => { e.preventDefault(); createDocMut.mutate({ ...docForm, client_id: clientId }) }}>
              <div>
                <label className="label">ประเภทเอกสาร</label>
                <select className="input" value={docForm.document_type} onChange={e => setDocForm((f: any) => ({ ...f, document_type: e.target.value }))}>
                  {DOCUMENT_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-grid-2">
                <div>
                  <label className="label">เดือน</label>
                  <select className="input" value={docForm.month || ''} onChange={e => setDocForm((f: any) => ({ ...f, month: e.target.value ? +e.target.value : undefined }))}>
                    <option value="">-- เลือก --</option>
                    {MONTH_NAMES_TH.slice(1).map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">ปี</label>
                  <input className="input" type="number" value={docForm.year || ''} onChange={e => setDocForm((f: any) => ({ ...f, year: e.target.value ? +e.target.value : undefined }))} />
                </div>
              </div>
              <div className="form-grid-2">
                <div><label className="label">จำนวน (ใบ)</label><input className="input" type="number" value={docForm.quantity} onChange={e => setDocForm((f: any) => ({ ...f, quantity: +e.target.value }))} /></div>
                <div><label className="label">วันที่รับ</label><input className="input" type="date" value={docForm.received_date || ''} onChange={e => setDocForm((f: any) => ({ ...f, received_date: e.target.value }))} /></div>
              </div>
              <div><label className="label">คำอธิบาย</label><input className="input" value={docForm.description || ''} onChange={e => setDocForm((f: any) => ({ ...f, description: e.target.value }))} /></div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowDocModal(false)}>ยกเลิก</button>
                <button type="submit" className="btn-primary">บันทึก</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex gap-3">
      <span className="text-sm text-gray-500 w-36 shrink-0">{label}:</span>
      <span className="text-sm text-gray-900">{value || '-'}</span>
    </div>
  )
}
