from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String)
    email = Column(String)
    phone = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    clients = relationship("Client", back_populates="assigned_staff")
    monthly_jobs = relationship("MonthlyJob", back_populates="assigned_staff")
    annual_jobs = relationship("AnnualJob", back_populates="assigned_staff")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)         # รหัสลูกค้า AC001
    name = Column(String, nullable=False)                  # ชื่อกิจการ
    tax_id = Column(String)                                # เลขที่ผู้เสียภาษี
    business_type = Column(String, default="บริษัทจำกัด")  # ประเภทธุรกิจ
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    contact_person = Column(String)
    service_package = Column(String)
    monthly_fee = Column(Float, default=0)
    annual_fee = Column(Float, default=0)
    vat_registered = Column(Boolean, default=False)        # จดภาษีมูลค่าเพิ่ม
    has_employees = Column(Boolean, default=False)         # มีพนักงาน
    fiscal_year_end = Column(Integer, default=12)          # เดือนสิ้นปีบัญชี
    start_date = Column(Date)
    status = Column(String, default="active")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    assigned_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    assigned_staff = relationship("Staff", back_populates="clients")

    monthly_jobs = relationship("MonthlyJob", back_populates="client", cascade="all, delete-orphan")
    annual_jobs = relationship("AnnualJob", back_populates="client", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    tax_filings = relationship("TaxFiling", back_populates="client", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="client", cascade="all, delete-orphan")
    wht_records = relationship("WHTRecord", back_populates="client", cascade="all, delete-orphan")


class MonthlyJob(Base):
    __tablename__ = "monthly_jobs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    documents_received = Column(Boolean, default=False)
    documents_received_date = Column(Date, nullable=True)

    bookkeeping_done = Column(Boolean, default=False)
    bookkeeping_done_date = Column(Date, nullable=True)

    vat_filed = Column(Boolean, default=False)
    vat_filed_date = Column(Date, nullable=True)
    vat_amount = Column(Float, nullable=True)

    wht_filed = Column(Boolean, default=False)
    wht_filed_date = Column(Date, nullable=True)

    sso_filed = Column(Boolean, default=False)
    sso_filed_date = Column(Date, nullable=True)
    sso_amount = Column(Float, nullable=True)

    financial_statement_done = Column(Boolean, default=False)
    financial_statement_done_date = Column(Date, nullable=True)

    status = Column(String, default="pending")
    assigned_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="monthly_jobs")
    assigned_staff = relationship("Staff", back_populates="monthly_jobs")


class AnnualJob(Base):
    __tablename__ = "annual_jobs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    year = Column(Integer, nullable=False)

    annual_fs_done = Column(Boolean, default=False)
    annual_fs_done_date = Column(Date, nullable=True)

    pnd51_filed = Column(Boolean, default=False)
    pnd51_filed_date = Column(Date, nullable=True)
    pnd51_amount = Column(Float, nullable=True)

    pnd50_filed = Column(Boolean, default=False)
    pnd50_filed_date = Column(Date, nullable=True)
    pnd50_amount = Column(Float, nullable=True)

    boj5_filed = Column(Boolean, default=False)
    boj5_filed_date = Column(Date, nullable=True)

    audit_required = Column(Boolean, default=False)
    audit_done = Column(Boolean, default=False)
    audit_done_date = Column(Date, nullable=True)
    auditor_name = Column(String, nullable=True)

    status = Column(String, default="pending")
    assigned_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="annual_jobs")
    assigned_staff = relationship("Staff", back_populates="annual_jobs")


# รายการซื้อ-ขาย (สำหรับสรุป VAT และ P&L)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    transaction_type = Column(String, nullable=False)  # income / expense
    date = Column(Date, nullable=False)
    document_number = Column(String)      # เลขที่เอกสาร
    counterparty = Column(String)         # คู่ค้า (ผู้ขาย/ผู้ซื้อ)
    counterparty_tax_id = Column(String)  # เลขที่ผู้เสียภาษีคู่ค้า
    description = Column(String)
    category = Column(String)             # หมวดรายได้/รายจ่าย
    amount = Column(Float, default=0)     # มูลค่าก่อนภาษี
    vat_rate = Column(Float, default=7)   # อัตรา VAT
    vat_amount = Column(Float, default=0) # ภาษีมูลค่าเพิ่ม
    total_amount = Column(Float, default=0)
    month = Column(Integer)
    year = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="transactions")


# ภาษีหัก ณ ที่จ่าย
class WHTRecord(Base):
    __tablename__ = "wht_records"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    wht_type = Column(String, nullable=False)   # ภงด.1 / ภงด.3 / ภงด.53
    direction = Column(String, nullable=False)  # issued (ออก) / received (รับ)
    date = Column(Date, nullable=False)
    payee_name = Column(String)       # ชื่อผู้รับเงิน
    payee_tax_id = Column(String)     # เลขที่ผู้เสียภาษีผู้รับเงิน
    income_type = Column(String)      # ประเภทเงินได้
    income_amount = Column(Float, default=0)
    wht_rate = Column(Float, default=3)
    wht_amount = Column(Float, default=0)
    month = Column(Integer)
    year = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="wht_records")


class TaxFiling(Base):
    __tablename__ = "tax_filings"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    filing_type = Column(String, nullable=False)  # ภพ.30 / ภงด.1 / ภงด.3 / ภงด.53 / ภงด.50 / ภงด.51 / บอจ.5
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=False)
    due_date = Column(Date)
    filed_date = Column(Date, nullable=True)
    amount = Column(Float, nullable=True)
    penalty = Column(Float, default=0)
    status = Column(String, default="pending")  # pending / filed / overdue
    reference_number = Column(String, nullable=True)
    notes = Column(Text)

    client = relationship("Client", back_populates="tax_filings")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    document_type = Column(String, nullable=False)
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    description = Column(String)
    received_date = Column(Date, nullable=True)
    quantity = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="documents")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    service_month = Column(Integer, nullable=True)
    service_year = Column(Integer, nullable=True)
    subtotal = Column(Float, default=0)
    vat_amount = Column(Float, default=0)
    total = Column(Float, default=0)
    status = Column(String, default="draft")  # draft / sent / paid / overdue
    paid_date = Column(Date, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0)
    amount = Column(Float, default=0)

    invoice = relationship("Invoice", back_populates="items")


class AutomationLog(Base):
    __tablename__ = "automation_logs"
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String, nullable=False)    # ชื่อ task ที่รัน
    trigger = Column(String, default="auto")      # auto / manual
    status = Column(String, default="success")    # success / error / warning
    message = Column(Text)                        # ผลลัพธ์
    details = Column(Text)                        # JSON รายละเอียด
    created_at = Column(DateTime, server_default=func.now())


class AutomationConfig(Base):
    __tablename__ = "automation_configs"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)   # ชื่อ setting
    value = Column(String)                              # ค่า
    description = Column(String)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
