export interface Staff {
  id: number
  name: string
  role?: string
  email?: string
  phone?: string
  active: boolean
  created_at?: string
}

export interface Client {
  id: number
  code: string
  name: string
  tax_id?: string
  business_type: string
  address?: string
  phone?: string
  email?: string
  contact_person?: string
  service_package?: string
  monthly_fee: number
  annual_fee: number
  vat_registered: boolean
  has_employees: boolean
  fiscal_year_end: number
  start_date?: string
  status: string
  notes?: string
  assigned_staff_id?: number
  assigned_staff?: Staff
  created_at?: string
}

export interface MonthlyJob {
  id: number
  client_id: number
  month: number
  year: number
  documents_received: boolean
  documents_received_date?: string
  bookkeeping_done: boolean
  bookkeeping_done_date?: string
  vat_filed: boolean
  vat_filed_date?: string
  vat_amount?: number
  wht_filed: boolean
  wht_filed_date?: string
  sso_filed: boolean
  sso_filed_date?: string
  sso_amount?: number
  financial_statement_done: boolean
  financial_statement_done_date?: string
  status: string
  assigned_staff_id?: number
  notes?: string
  client?: Client
  assigned_staff?: Staff
}

export interface AnnualJob {
  id: number
  client_id: number
  year: number
  annual_fs_done: boolean
  annual_fs_done_date?: string
  pnd51_filed: boolean
  pnd51_filed_date?: string
  pnd51_amount?: number
  pnd50_filed: boolean
  pnd50_filed_date?: string
  pnd50_amount?: number
  boj5_filed: boolean
  boj5_filed_date?: string
  audit_required: boolean
  audit_done: boolean
  audit_done_date?: string
  auditor_name?: string
  status: string
  assigned_staff_id?: number
  notes?: string
  client?: Client
  assigned_staff?: Staff
}

export interface Transaction {
  id: number
  client_id: number
  transaction_type: 'income' | 'expense'
  date: string
  document_number?: string
  counterparty?: string
  counterparty_tax_id?: string
  description?: string
  category?: string
  amount: number
  vat_rate: number
  vat_amount: number
  total_amount: number
  month?: number
  year?: number
  notes?: string
}

export interface WHTRecord {
  id: number
  client_id: number
  wht_type: string
  direction: string
  date: string
  payee_name?: string
  payee_tax_id?: string
  income_type?: string
  income_amount: number
  wht_rate: number
  wht_amount: number
  month?: number
  year?: number
  notes?: string
}

export interface TaxFiling {
  id: number
  client_id: number
  filing_type: string
  month?: number
  year: number
  due_date?: string
  filed_date?: string
  amount?: number
  penalty: number
  status: string
  reference_number?: string
  notes?: string
  client?: Client
}

export interface Document {
  id: number
  client_id: number
  document_type: string
  month?: number
  year?: number
  description?: string
  received_date?: string
  quantity: number
  notes?: string
}

export interface InvoiceItem {
  id: number
  description: string
  quantity: number
  unit_price: number
  amount: number
}

export interface Invoice {
  id: number
  invoice_number: string
  client_id: number
  invoice_date: string
  due_date?: string
  service_month?: number
  service_year?: number
  subtotal: number
  vat_amount: number
  total: number
  status: string
  paid_date?: string
  notes?: string
  client?: Client
  items: InvoiceItem[]
}

export interface DashboardStats {
  total_clients: number
  active_clients: number
  pending_monthly_jobs: number
  completed_monthly_jobs: number
  unpaid_invoices: number
  unpaid_amount: number
  this_month_income: number
  current_month: number
  current_year: number
}

export const MONTH_NAMES_TH = [
  '', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
  'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม',
]

export const MONTH_SHORT_TH = [
  '', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.',
  'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.',
]

export const BUSINESS_TYPES = [
  'บริษัทจำกัด',
  'ห้างหุ้นส่วนจำกัด',
  'บุคคลธรรมดา',
  'อื่นๆ',
]

export const INCOME_CATEGORIES = [
  'รายได้จากการขาย',
  'รายได้จากบริการ',
  'รายได้อื่น',
]

export const EXPENSE_CATEGORIES = [
  'ค่าสินค้า/วัตถุดิบ',
  'ค่าเช่า',
  'ค่าไฟฟ้า/น้ำ/โทรศัพท์',
  'ค่าเงินเดือนพนักงาน',
  'ค่าการตลาด/โฆษณา',
  'ค่าขนส่ง',
  'ค่าซ่อมบำรุง',
  'ค่าใช้จ่ายทั่วไป',
  'อื่นๆ',
]

export const WHT_TYPES = ['ภงด.1', 'ภงด.3', 'ภงด.53']

export const INCOME_TYPES_WHT = [
  '40(1) เงินเดือน',
  '40(2) ค่าจ้าง',
  '40(3) ค่าลิขสิทธิ์',
  '40(5) ค่าเช่า',
  '40(6) วิชาชีพอิสระ',
  '40(7) รับเหมา',
  '40(8) อื่นๆ',
]

export const DOCUMENT_TYPES = [
  'ใบเสร็จรับเงิน / ใบกำกับภาษี',
  'ใบแจ้งหนี้',
  'Statement ธนาคาร',
  'เอกสารเงินเดือน',
  'ใบสำคัญจ่าย',
  'เอกสารอื่นๆ',
]
