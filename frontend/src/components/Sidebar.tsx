import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, ClipboardList, Calendar,
  FileText, Receipt, UserCog, BookOpen, Zap, ScanLine,
} from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'หน้าหลัก' },
  { to: '/clients', icon: Users, label: 'ลูกค้า' },
  { to: '/monthly-jobs', icon: ClipboardList, label: 'งานรายเดือน' },
  { to: '/annual-jobs', icon: BookOpen, label: 'งานประจำปี' },
  { to: '/tax-calendar', icon: Calendar, label: 'ปฏิทินภาษี' },
  { to: '/invoices', icon: Receipt, label: 'ใบแจ้งหนี้' },
  { to: '/bill-scan', icon: ScanLine, label: 'อ่านบิล PDF' },
  { to: '/automation', icon: Zap, label: 'Automation' },
  { to: '/staff', icon: UserCog, label: 'พนักงาน' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-indigo-900 text-white flex flex-col shrink-0">
      <div className="p-5 border-b border-indigo-800">
        <div className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-indigo-300" />
          <div>
            <div className="font-bold text-sm leading-tight">สำนักงานบัญชี</div>
            <div className="text-indigo-400 text-xs">ระบบบริหารจัดการ</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-700 text-white'
                  : 'text-indigo-200 hover:bg-indigo-800 hover:text-white'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-indigo-800 text-indigo-400 text-xs text-center">
        v1.0.0
      </div>
    </aside>
  )
}
