from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import (
    clients, staff, monthly_jobs, annual_jobs, tax_filings,
    documents, invoices, dashboard, transactions, wht_records,
    automation,
)
from scheduler import setup_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # เริ่มต้น scheduler เมื่อ server start
    sched = setup_scheduler()
    yield
    # หยุด scheduler เมื่อ server shutdown
    sched.shutdown()


app = FastAPI(
    title="ระบบบริหารจัดการสำนักงานบัญชี",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(staff.router, prefix="/api/staff", tags=["staff"])
app.include_router(monthly_jobs.router, prefix="/api/monthly-jobs", tags=["monthly-jobs"])
app.include_router(annual_jobs.router, prefix="/api/annual-jobs", tags=["annual-jobs"])
app.include_router(tax_filings.router, prefix="/api/tax-filings", tags=["tax-filings"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(wht_records.router, prefix="/api/wht-records", tags=["wht-records"])
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])


@app.get("/")
def root():
    return {"message": "ระบบบริหารจัดการสำนักงานบัญชี API"}
