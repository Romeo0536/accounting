import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import ClientDetail from './pages/ClientDetail'
import MonthlyJobs from './pages/MonthlyJobs'
import AnnualJobs from './pages/AnnualJobs'
import TaxCalendar from './pages/TaxCalendar'
import Invoices from './pages/Invoices'
import StaffPage from './pages/Staff'
import Automation from './pages/Automation'
import LineBot from './pages/LineBot'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="clients" element={<Clients />} />
          <Route path="clients/:id" element={<ClientDetail />} />
          <Route path="monthly-jobs" element={<MonthlyJobs />} />
          <Route path="annual-jobs" element={<AnnualJobs />} />
          <Route path="tax-calendar" element={<TaxCalendar />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="automation" element={<Automation />} />
          <Route path="line-bot" element={<LineBot />} />
          <Route path="staff" element={<StaffPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
