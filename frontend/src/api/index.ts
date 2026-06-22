import axios from 'axios'
import type {
  Client, Staff, MonthlyJob, AnnualJob, Transaction,
  WHTRecord, TaxFiling, Document, Invoice, DashboardStats,
} from '../types'

const api = axios.create({ baseURL: '/api' })

// Dashboard
export const getDashboardStats = () => api.get<DashboardStats>('/dashboard/stats').then(r => r.data)
export const getPendingJobs = () => api.get<any[]>('/dashboard/pending-jobs').then(r => r.data)
export const getUpcomingDeadlines = () => api.get<any[]>('/dashboard/upcoming-deadlines').then(r => r.data)
export const getUnpaidInvoices = () => api.get<any[]>('/dashboard/unpaid-invoices').then(r => r.data)

// Clients
export const getClients = (status?: string) =>
  api.get<Client[]>('/clients', { params: { status } }).then(r => r.data)
export const getClient = (id: number) => api.get<Client>(`/clients/${id}`).then(r => r.data)
export const createClient = (data: Partial<Client>) => api.post<Client>('/clients', data).then(r => r.data)
export const updateClient = (id: number, data: Partial<Client>) =>
  api.put<Client>(`/clients/${id}`, data).then(r => r.data)
export const deleteClient = (id: number) => api.delete(`/clients/${id}`)

// Staff
export const getStaff = () => api.get<Staff[]>('/staff').then(r => r.data)
export const createStaff = (data: Partial<Staff>) => api.post<Staff>('/staff', data).then(r => r.data)
export const updateStaff = (id: number, data: Partial<Staff>) =>
  api.put<Staff>(`/staff/${id}`, data).then(r => r.data)
export const deleteStaff = (id: number) => api.delete(`/staff/${id}`)

// Monthly Jobs
export const getMonthlyJobs = (params?: { month?: number; year?: number; client_id?: number; status?: string }) =>
  api.get<MonthlyJob[]>('/monthly-jobs', { params }).then(r => r.data)
export const createMonthlyJob = (data: Partial<MonthlyJob>) =>
  api.post<MonthlyJob>('/monthly-jobs', data).then(r => r.data)
export const bulkCreateMonthlyJobs = (month: number, year: number) =>
  api.post('/monthly-jobs/bulk-create', null, { params: { month, year } }).then(r => r.data)
export const updateMonthlyJob = (id: number, data: Partial<MonthlyJob>) =>
  api.put<MonthlyJob>(`/monthly-jobs/${id}`, data).then(r => r.data)
export const deleteMonthlyJob = (id: number) => api.delete(`/monthly-jobs/${id}`)

// Annual Jobs
export const getAnnualJobs = (params?: { year?: number; client_id?: number; status?: string }) =>
  api.get<AnnualJob[]>('/annual-jobs', { params }).then(r => r.data)
export const createAnnualJob = (data: Partial<AnnualJob>) =>
  api.post<AnnualJob>('/annual-jobs', data).then(r => r.data)
export const bulkCreateAnnualJobs = (year: number) =>
  api.post('/annual-jobs/bulk-create', null, { params: { year } }).then(r => r.data)
export const updateAnnualJob = (id: number, data: Partial<AnnualJob>) =>
  api.put<AnnualJob>(`/annual-jobs/${id}`, data).then(r => r.data)

// Transactions
export const getTransactions = (params?: { client_id?: number; month?: number; year?: number; transaction_type?: string }) =>
  api.get<Transaction[]>('/transactions', { params }).then(r => r.data)
export const createTransaction = (data: Partial<Transaction>) =>
  api.post<Transaction>('/transactions', data).then(r => r.data)
export const updateTransaction = (id: number, data: Partial<Transaction>) =>
  api.put<Transaction>(`/transactions/${id}`, data).then(r => r.data)
export const deleteTransaction = (id: number) => api.delete(`/transactions/${id}`)
export const getTransactionSummary = (client_id: number, month: number, year: number) =>
  api.get('/transactions/summary', { params: { client_id, month, year } }).then(r => r.data)
export const getAnnualSummary = (client_id: number, year: number) =>
  api.get('/transactions/annual-summary', { params: { client_id, year } }).then(r => r.data)

// WHT Records
export const getWHTRecords = (params?: { client_id?: number; month?: number; year?: number }) =>
  api.get<WHTRecord[]>('/wht-records', { params }).then(r => r.data)
export const createWHTRecord = (data: Partial<WHTRecord>) =>
  api.post<WHTRecord>('/wht-records', data).then(r => r.data)
export const updateWHTRecord = (id: number, data: Partial<WHTRecord>) =>
  api.put<WHTRecord>(`/wht-records/${id}`, data).then(r => r.data)
export const deleteWHTRecord = (id: number) => api.delete(`/wht-records/${id}`)

// Tax Filings
export const getTaxFilings = (params?: { client_id?: number; month?: number; year?: number; status?: string }) =>
  api.get<TaxFiling[]>('/tax-filings', { params }).then(r => r.data)
export const createTaxFiling = (data: Partial<TaxFiling>) =>
  api.post<TaxFiling>('/tax-filings', data).then(r => r.data)
export const updateTaxFiling = (id: number, data: Partial<TaxFiling>) =>
  api.put<TaxFiling>(`/tax-filings/${id}`, data).then(r => r.data)
export const deleteTaxFiling = (id: number) => api.delete(`/tax-filings/${id}`)

// Documents
export const getDocuments = (params?: { client_id?: number; month?: number; year?: number }) =>
  api.get<Document[]>('/documents', { params }).then(r => r.data)
export const createDocument = (data: Partial<Document>) =>
  api.post<Document>('/documents', data).then(r => r.data)
export const updateDocument = (id: number, data: Partial<Document>) =>
  api.put<Document>(`/documents/${id}`, data).then(r => r.data)
export const deleteDocument = (id: number) => api.delete(`/documents/${id}`)

// Invoices
export const getInvoices = (params?: { client_id?: number; status?: string; year?: number }) =>
  api.get<Invoice[]>('/invoices', { params }).then(r => r.data)
export const createInvoice = (data: any) => api.post<Invoice>('/invoices', data).then(r => r.data)
export const updateInvoice = (id: number, data: Partial<Invoice>) =>
  api.put<Invoice>(`/invoices/${id}`, data).then(r => r.data)
export const markInvoicePaid = (id: number, paid_date?: string) =>
  api.post<Invoice>(`/invoices/${id}/mark-paid`, null, { params: { paid_date } }).then(r => r.data)
export const deleteInvoice = (id: number) => api.delete(`/invoices/${id}`)

// LINE Bot
export const getLineStatus = () => api.get('/line/status').then(r => r.data)
export const getLineCommands = () => api.get<{ commands: any[] }>('/line/commands').then(r => r.data)
export const simulateLine = (text: string) =>
  api.post<{ reply: string; quick_replies: string[] }>('/line/simulate', { text }).then(r => r.data)
export const getLineConfig = () => api.get<{ default_to: string }>('/line/config').then(r => r.data)
export const setLineConfig = (default_to: string) =>
  api.post('/line/config', { default_to }).then(r => r.data)
export const pushLineDaily = () => api.post('/line/push-daily').then(r => r.data)

export default api
