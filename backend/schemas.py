from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


# ---- Staff ----
class StaffBase(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: bool = True


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: Optional[bool] = None


class StaffResponse(StaffBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Client ----
class ClientBase(BaseModel):
    name: str
    tax_id: Optional[str] = None
    business_type: str = "บริษัทจำกัด"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    service_package: Optional[str] = None
    monthly_fee: float = 0
    annual_fee: float = 0
    vat_registered: bool = False
    has_employees: bool = False
    fiscal_year_end: int = 12
    start_date: Optional[date] = None
    status: str = "active"
    notes: Optional[str] = None
    assigned_staff_id: Optional[int] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    service_package: Optional[str] = None
    monthly_fee: Optional[float] = None
    annual_fee: Optional[float] = None
    vat_registered: Optional[bool] = None
    has_employees: Optional[bool] = None
    fiscal_year_end: Optional[int] = None
    start_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_staff_id: Optional[int] = None


class ClientResponse(ClientBase):
    id: int
    code: str
    created_at: Optional[datetime] = None
    assigned_staff: Optional[StaffResponse] = None

    model_config = {"from_attributes": True}


# ---- MonthlyJob ----
class MonthlyJobBase(BaseModel):
    client_id: int
    month: int
    year: int
    documents_received: bool = False
    documents_received_date: Optional[date] = None
    bookkeeping_done: bool = False
    bookkeeping_done_date: Optional[date] = None
    vat_filed: bool = False
    vat_filed_date: Optional[date] = None
    vat_amount: Optional[float] = None
    wht_filed: bool = False
    wht_filed_date: Optional[date] = None
    sso_filed: bool = False
    sso_filed_date: Optional[date] = None
    sso_amount: Optional[float] = None
    financial_statement_done: bool = False
    financial_statement_done_date: Optional[date] = None
    status: str = "pending"
    assigned_staff_id: Optional[int] = None
    notes: Optional[str] = None


class MonthlyJobCreate(MonthlyJobBase):
    pass


class MonthlyJobUpdate(BaseModel):
    documents_received: Optional[bool] = None
    documents_received_date: Optional[date] = None
    bookkeeping_done: Optional[bool] = None
    bookkeeping_done_date: Optional[date] = None
    vat_filed: Optional[bool] = None
    vat_filed_date: Optional[date] = None
    vat_amount: Optional[float] = None
    wht_filed: Optional[bool] = None
    wht_filed_date: Optional[date] = None
    sso_filed: Optional[bool] = None
    sso_filed_date: Optional[date] = None
    sso_amount: Optional[float] = None
    financial_statement_done: Optional[bool] = None
    financial_statement_done_date: Optional[date] = None
    status: Optional[str] = None
    assigned_staff_id: Optional[int] = None
    notes: Optional[str] = None


class MonthlyJobResponse(MonthlyJobBase):
    id: int
    created_at: Optional[datetime] = None
    client: Optional[ClientResponse] = None
    assigned_staff: Optional[StaffResponse] = None

    model_config = {"from_attributes": True}


# ---- AnnualJob ----
class AnnualJobBase(BaseModel):
    client_id: int
    year: int
    annual_fs_done: bool = False
    annual_fs_done_date: Optional[date] = None
    pnd51_filed: bool = False
    pnd51_filed_date: Optional[date] = None
    pnd51_amount: Optional[float] = None
    pnd50_filed: bool = False
    pnd50_filed_date: Optional[date] = None
    pnd50_amount: Optional[float] = None
    boj5_filed: bool = False
    boj5_filed_date: Optional[date] = None
    audit_required: bool = False
    audit_done: bool = False
    audit_done_date: Optional[date] = None
    auditor_name: Optional[str] = None
    status: str = "pending"
    assigned_staff_id: Optional[int] = None
    notes: Optional[str] = None


class AnnualJobCreate(AnnualJobBase):
    pass


class AnnualJobUpdate(BaseModel):
    annual_fs_done: Optional[bool] = None
    annual_fs_done_date: Optional[date] = None
    pnd51_filed: Optional[bool] = None
    pnd51_filed_date: Optional[date] = None
    pnd51_amount: Optional[float] = None
    pnd50_filed: Optional[bool] = None
    pnd50_filed_date: Optional[date] = None
    pnd50_amount: Optional[float] = None
    boj5_filed: Optional[bool] = None
    boj5_filed_date: Optional[date] = None
    audit_required: Optional[bool] = None
    audit_done: Optional[bool] = None
    audit_done_date: Optional[date] = None
    auditor_name: Optional[str] = None
    status: Optional[str] = None
    assigned_staff_id: Optional[int] = None
    notes: Optional[str] = None


class AnnualJobResponse(AnnualJobBase):
    id: int
    created_at: Optional[datetime] = None
    client: Optional[ClientResponse] = None
    assigned_staff: Optional[StaffResponse] = None

    model_config = {"from_attributes": True}


# ---- Transaction ----
class TransactionBase(BaseModel):
    client_id: int
    transaction_type: str  # income / expense
    date: date
    document_number: Optional[str] = None
    counterparty: Optional[str] = None
    counterparty_tax_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    amount: float = 0
    vat_rate: float = 7
    vat_amount: float = 0
    total_amount: float = 0
    month: Optional[int] = None
    year: Optional[int] = None
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    transaction_type: Optional[str] = None
    date: Optional[date] = None
    document_number: Optional[str] = None
    counterparty: Optional[str] = None
    counterparty_tax_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    total_amount: Optional[float] = None
    notes: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- WHTRecord ----
class WHTRecordBase(BaseModel):
    client_id: int
    wht_type: str       # ภงด.1 / ภงด.3 / ภงด.53
    direction: str      # issued / received
    date: date
    payee_name: Optional[str] = None
    payee_tax_id: Optional[str] = None
    income_type: Optional[str] = None
    income_amount: float = 0
    wht_rate: float = 3
    wht_amount: float = 0
    month: Optional[int] = None
    year: Optional[int] = None
    notes: Optional[str] = None


class WHTRecordCreate(WHTRecordBase):
    pass


class WHTRecordUpdate(BaseModel):
    wht_type: Optional[str] = None
    direction: Optional[str] = None
    date: Optional[date] = None
    payee_name: Optional[str] = None
    payee_tax_id: Optional[str] = None
    income_type: Optional[str] = None
    income_amount: Optional[float] = None
    wht_rate: Optional[float] = None
    wht_amount: Optional[float] = None
    notes: Optional[str] = None


class WHTRecordResponse(WHTRecordBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- TaxFiling ----
class TaxFilingBase(BaseModel):
    client_id: int
    filing_type: str
    month: Optional[int] = None
    year: int
    due_date: Optional[date] = None
    filed_date: Optional[date] = None
    amount: Optional[float] = None
    penalty: float = 0
    status: str = "pending"
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class TaxFilingCreate(TaxFilingBase):
    pass


class TaxFilingUpdate(BaseModel):
    filed_date: Optional[date] = None
    amount: Optional[float] = None
    penalty: Optional[float] = None
    status: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class TaxFilingResponse(TaxFilingBase):
    id: int
    client: Optional[ClientResponse] = None

    model_config = {"from_attributes": True}


# ---- Document ----
class DocumentBase(BaseModel):
    client_id: int
    document_type: str
    month: Optional[int] = None
    year: Optional[int] = None
    description: Optional[str] = None
    received_date: Optional[date] = None
    quantity: int = 0
    notes: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    month: Optional[int] = None
    year: Optional[int] = None
    description: Optional[str] = None
    received_date: Optional[date] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Invoice ----
class InvoiceItemBase(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float = 0
    amount: float = 0


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: int

    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    client_id: int
    invoice_date: date
    due_date: Optional[date] = None
    service_month: Optional[int] = None
    service_year: Optional[int] = None
    subtotal: float = 0
    vat_amount: float = 0
    total: float = 0
    status: str = "draft"
    paid_date: Optional[date] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    service_month: Optional[int] = None
    service_year: Optional[int] = None
    subtotal: Optional[float] = None
    vat_amount: Optional[float] = None
    total: Optional[float] = None
    status: Optional[str] = None
    paid_date: Optional[date] = None
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceResponse(InvoiceBase):
    id: int
    invoice_number: str
    created_at: Optional[datetime] = None
    client: Optional[ClientResponse] = None
    items: List[InvoiceItemResponse] = []

    model_config = {"from_attributes": True}


# ---- Dashboard ----
class DashboardStats(BaseModel):
    total_clients: int
    active_clients: int
    pending_monthly_jobs: int
    completed_monthly_jobs: int
    overdue_jobs: int
    unpaid_invoices: int
    unpaid_amount: float
    this_month_income: float
