import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Calendar,
  BookOpen,
  FileText,
  BarChart3,
  MessageSquare,
  Settings,
  LogOut,
  Bell,
  Menu,
  X,
  GraduationCap,
  Megaphone,
  ScrollText,
  Layers,
} from 'lucide-react'
import { logout, Role } from '@/lib/auth'
import { getUser } from '@/lib/auth'
import { GlobalSearch } from './GlobalSearch'

const ROLE_CONFIG: Record<Role, {
  name: string
  icon: React.ComponentType<{ className?: string }>
  nav: { label: string; path: string; icon: React.ComponentType<{ className?: string }> }[]
}> = {
  ADMIN: {
    name: 'Admin',
    icon: GraduationCap,
    nav: [
      { label: 'Dashboard', path: '', icon: LayoutDashboard },
      { label: 'Users', path: 'users', icon: Users },
      { label: 'Students', path: 'students', icon: GraduationCap },
      { label: 'Faculty', path: 'faculty', icon: Users },
      { label: 'Departments', path: 'departments', icon: BarChart3 },
      { label: 'Courses', path: 'courses', icon: BookOpen },
      { label: 'Sections', path: 'sections', icon: Layers },
      { label: 'Subjects', path: 'subjects', icon: BookOpen },
      { label: 'Announcements', path: 'announcements', icon: Megaphone },
      { label: 'Reports', path: 'reports', icon: FileText },
      { label: 'Audit Logs', path: 'audit-logs', icon: ScrollText },
      { label: 'Settings', path: 'settings', icon: Settings },
    ],
  },
  HOD: {
    name: 'Head of Department',
    icon: BarChart3,
    nav: [
      { label: 'Dashboard', path: '', icon: LayoutDashboard },
      { label: 'Students', path: 'students', icon: GraduationCap },
      { label: 'Faculty', path: 'faculty', icon: Users },
      { label: 'Subjects', path: 'subjects', icon: BookOpen },
      { label: 'Attendance', path: 'attendance', icon: Calendar },
      { label: 'Performance', path: 'performance', icon: BarChart3 },
      { label: 'Timetable', path: 'timetable', icon: Calendar },
      { label: 'Announcements', path: 'announcements', icon: Megaphone },
      { label: 'Reports', path: 'reports', icon: FileText },
    ],
  },
  FACULTY: {
    name: 'Faculty',
    icon: Users,
    nav: [
      { label: 'Dashboard', path: '', icon: LayoutDashboard },
      { label: 'My Subjects', path: 'subjects', icon: BookOpen },
      { label: 'Attendance', path: 'attendance', icon: Calendar },
      { label: 'Assignments', path: 'assignments', icon: FileText },
      { label: 'Projects', path: 'projects', icon: FileText },
      { label: 'Announcements', path: 'announcements', icon: Megaphone },
      { label: 'Notifications', path: 'notifications', icon: Bell },
      { label: 'AI Assistant', path: 'ai', icon: MessageSquare },
    ],
  },
  CR: {
    name: 'Class Representative',
    icon: Bell,
    nav: [
      { label: 'Dashboard', path: '', icon: LayoutDashboard },
      { label: 'Attendance', path: 'attendance', icon: Calendar },
      { label: 'Timetable', path: 'timetable', icon: Calendar },
      { label: 'Announcements', path: 'announcements', icon: Megaphone },
      { label: 'Assignments', path: 'assignments', icon: FileText },
      { label: 'Class Requests', path: 'requests', icon: FileText },
      { label: 'Feedback', path: 'feedback', icon: MessageSquare },
      { label: 'Notifications', path: 'notifications', icon: Bell },
    ],
  },
  STUDENT: {
    name: 'Student',
    icon: GraduationCap,
    nav: [
      { label: 'Dashboard', path: '', icon: LayoutDashboard },
      { label: 'Attendance', path: 'attendance', icon: Calendar },
      { label: 'Timetable', path: 'timetable', icon: Calendar },
      { label: 'Assignments', path: 'assignments', icon: FileText },
      { label: 'Projects', path: 'projects', icon: FileText },
      { label: 'Announcements', path: 'announcements', icon: Megaphone },
      { label: 'Notifications', path: 'notifications', icon: Bell },
      { label: 'AI Assistant', path: 'ai', icon: MessageSquare },
    ],
  },
}

function Layout({ children, role }: { children: React.ReactNode; role: Role }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const config = ROLE_CONFIG[role]
  const basePath = `/${role.toLowerCase()}`
  const currentUser = getUser()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Top navbar (desktop) */}
      <header className="sticky top-0 z-30 hidden border-b border-gray-200 bg-white/95 backdrop-blur dark:border-gray-700 dark:bg-gray-800/95 md:block">
        <div className="flex h-16 items-center gap-4 px-6">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 lg:hidden"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <GlobalSearch />
          <div className="ml-auto flex items-center gap-3">
            {currentUser && (
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-sm font-semibold text-white">
                  {currentUser.name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden text-right lg:block">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{currentUser.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{config.name}</p>
                </div>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden lg:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 md:hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <config.icon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold text-gray-900 dark:text-white">{config.name}</span>
          </div>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`
            fixed md:sticky md:top-16 md:h-[calc(100vh-4rem)] inset-y-0 left-0 z-40
            w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700
            transform transition-transform duration-200
            ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          `}
        >
          <div className="flex flex-col h-full">
            {/* Logo */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <config.icon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="font-bold text-gray-900 dark:text-white">CampusIQ</h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{config.name}</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
              {config.nav.map((item) => {
                const itemPath = item.path ? `${basePath}/${item.path}` : `${basePath}`
                const isActive =
                  location.pathname === itemPath ||
                  (item.path === '' && (location.pathname === basePath || location.pathname === `${basePath}/`))
                return (
                  <Link
                    key={item.path}
                    to={itemPath}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`
                      flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                      transition-colors
                      ${isActive
                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}
                    `}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.label}
                  </Link>
                )
              })}
            </nav>

            {/* User section (mobile only - desktop uses the top navbar) */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 md:hidden">
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </div>
        </aside>

        {/* Overlay for mobile */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 min-w-0">
          <div className="max-w-7xl mx-auto p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
