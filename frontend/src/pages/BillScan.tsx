import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { parseBillPdf } from '../api'
import type { ParsedBill, ParsedBillItem } from '../api'

function formatMoney(n?: number) {
  return (n ?? 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })
}

export default function BillScan() {
  const [fileName, setFileName] = useState('')
  const [bill, setBill] = useState<ParsedBill | null>(null)

  const parseMut = useMutation({
    mutationFn: parseBillPdf,
    onSuccess: (res) => setBill(res.parsed),
  })

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setBill(null)
    parseMut.mutate(file)
  }

  // อนุญาตให้ผู้ใช้แก้ไขค่าที่อ่านได้ก่อน (preview)
  const updateField = (field: keyof ParsedBill, value: string | number) =>
    setBill((b) => (b ? { ...b, [field]: value } : b))

  const updateItem = (idx: number, field: keyof ParsedBillItem, value: string | number) =>
    setBill((b) => {
      if (!b) return b
      const items = [...b.items]
      items[idx] = { ...items[idx], [field]: value }
      return { ...b, items }
    })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">อ่านบิลจาก PDF</h1>
        <p className="text-gray-500 text-sm mt-1">
          อัปโหลดใบกำกับภาษี/ใบเสร็จ (PDF) ระบบจะอ่านข้อมูลออกมาเป็นตารางให้ตรวจสอบ
        </p>
      </div>

      {/* Upload */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <label className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-gray-300 rounded-lg p-8 cursor-pointer hover:border-indigo-400 transition-colors">
          <Upload className="w-8 h-8 text-gray-400" />
          <span className="text-sm text-gray-600">คลิกเพื่อเลือกไฟล์ PDF</span>
          <input type="file" accept="application/pdf" className="hidden" onChange={handleFile} />
        </label>
        {fileName && (
          <div className="flex items-center gap-2 mt-3 text-sm text-gray-600">
            <FileText className="w-4 h-4" /> {fileName}
          </div>
        )}
      </div>

      {parseMut.isPending && (
        <div className="flex items-center gap-2 text-indigo-600">
          <Loader2 className="w-5 h-5 animate-spin" /> กำลังอ่านบิล...
        </div>
      )}

      {parseMut.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
          อ่านบิลไม่สำเร็จ: {(parseMut.error as any)?.response?.data?.detail ?? 'เกิดข้อผิดพลาด'}
        </div>
      )}

      {/* Preview */}
      {bill && (
        <div className="space-y-6">
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h3 className="font-semibold mb-4">ข้อมูลที่อ่านได้ (แก้ไขได้)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">ชื่อผู้ขาย</label>
                <input className="input" value={bill.vendor_name}
                  onChange={(e) => updateField('vendor_name', e.target.value)} />
              </div>
              <div>
                <label className="label">เลขผู้เสียภาษี</label>
                <input className="input" value={bill.vendor_tax_id ?? ''}
                  onChange={(e) => updateField('vendor_tax_id', e.target.value)} />
              </div>
              <div>
                <label className="label">เลขที่เอกสาร</label>
                <input className="input" value={bill.doc_number}
                  onChange={(e) => updateField('doc_number', e.target.value)} />
              </div>
              <div>
                <label className="label">วันที่</label>
                <input className="input" type="date" value={bill.doc_date}
                  onChange={(e) => updateField('doc_date', e.target.value)} />
              </div>
            </div>
          </div>

          {/* Items table */}
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>รายการ</th>
                  <th className="text-right">จำนวน</th>
                  <th className="text-right">ราคา/หน่วย</th>
                  <th className="text-right">จำนวนเงิน</th>
                </tr>
              </thead>
              <tbody>
                {bill.items.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <input className="input" value={item.description}
                        onChange={(e) => updateItem(idx, 'description', e.target.value)} />
                    </td>
                    <td className="text-right">
                      <input className="input text-right" type="number" value={item.quantity ?? 0}
                        onChange={(e) => updateItem(idx, 'quantity', +e.target.value)} />
                    </td>
                    <td className="text-right">
                      <input className="input text-right" type="number" value={item.unit_price ?? 0}
                        onChange={(e) => updateItem(idx, 'unit_price', +e.target.value)} />
                    </td>
                    <td className="text-right">
                      <input className="input text-right" type="number" value={item.amount}
                        onChange={(e) => updateItem(idx, 'amount', +e.target.value)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {bill.items.length === 0 && (
              <div className="p-6 text-center text-gray-400">ไม่พบรายการในบิล</div>
            )}
          </div>

          {/* Summary */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm max-w-sm ml-auto">
            <div className="flex justify-between"><span>ยอดก่อน VAT:</span><span>฿{formatMoney(bill.sub_total)}</span></div>
            <div className="flex justify-between"><span>VAT 7%:</span><span>฿{formatMoney(bill.vat_amount)}</span></div>
            <div className="flex justify-between font-bold text-base border-t border-gray-200 pt-2 mt-2">
              <span>รวมทั้งสิ้น:</span><span className="text-indigo-600">฿{formatMoney(bill.grand_total)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
