import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { isAuthenticated, getRole, Role } from '@/lib/auth'
import Layout from '@/components/layout/Layout'
import Login from '@/pages/Login'
import StudentDashboard from '@/pages/student/Dashboard'
import StudentProjects from '@/pages/student/Projects'
import StudentProjectDetail from '@/pages/student/ProjectDetail'
import StudentAttendance from '@/pages/student/Attendance'
import StudentTimetable from '@/pages/student/Timetable'
import StudentAssignments from '@/pages/student/Assignments'
import StudentAnnouncements from '@/pages/student/Announcements'
import FacultyDashboard from '@/pages/faculty/Dashboard'
import FacultyProjects from '@/pages/faculty/Projects'
import FacultyProjectDetail from '@/pages/faculty/ProjectDetail'
import FacultyAttendance from '@/pages/faculty/Attendance'
import FacultyAssignments from '@/pages/faculty/Assignments'
import FacultyTimetable from '@/pages/faculty/Timetable'
import FacultyMarks from '@/pages/faculty/Marks'
import FacultySubjects from '@/pages/faculty/Subjects'
import FacultyAnnouncements from '@/pages/faculty/Announcements'
import FacultyReports from '@/pages/faculty/Reports'
import CRDashboard from '@/pages/cr/Dashboard'
import CRAnnouncements from '@/pages/cr/Announcements'
import CRAttendance from '@/pages/cr/Attendance'
import CRTimetable from '@/pages/cr/Timetable'
import CRAssignments from '@/pages/cr/Assignments'
import CRRequests from '@/pages/cr/Requests'
import CRFeedback from '@/pages/cr/Feedback'
import HODDashboard from '@/pages/hod/Dashboard'
import HODAnnouncements from '@/pages/hod/Announcements'
import HODReports from '@/pages/hod/Reports'
import HODStudents from '@/pages/hod/Students'
import HODFaculty from '@/pages/hod/Faculty'
import HODSubjects from '@/pages/hod/Subjects'
import HODAttendance from '@/pages/hod/Attendance'
import HODPerformance from '@/pages/hod/Performance'
import HODTimetable from '@/pages/hod/Timetable'
import AdminDashboard from '@/pages/admin/Dashboard'
import AdminTimetable from '@/pages/admin/Timetable'
import AdminAnnouncements from '@/pages/admin/Announcements'
import AdminReports from '@/pages/admin/Reports'
import AdminUsers from '@/pages/admin/Users'
import AdminStudents from '@/pages/admin/Students'
import AdminFaculty from '@/pages/admin/Faculty'
import AdminAuditLogs from '@/pages/admin/AuditLogs'
import AdminDepartments from '@/pages/admin/Departments'
import AdminCourses from '@/pages/admin/Courses'
import AdminSubjects from '@/pages/admin/Subjects'
import AdminSettings from '@/pages/admin/Settings'
import Notifications from '@/pages/Notifications'
import AIAssistant from '@/pages/AIAssistant'
import NotFound from '@/pages/NotFound'

function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode
  allowedRoles: Role[]
}) {
  const [isAuth, setIsAuth] = useState<boolean | null>(null)
  const [role, setRole] = useState<Role | null>(null)

  useEffect(() => {
    setIsAuth(isAuthenticated())
    setRole(getRole())
  }, [])

  if (isAuth === null) return <div className="p-8">Loading...</div>

  if (!isAuth) return <Navigate to="/login" replace />

  if (role && !allowedRoles.includes(role)) return <Navigate to="/unauthorized" replace />

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/unauthorized" element={<NotFound />} />
      
      {/* Student Routes */}
      <Route path="/student/*" element={
        <ProtectedRoute allowedRoles={['STUDENT']}>
          <Layout role="STUDENT">
            <Routes>
              <Route path="/" element={<StudentDashboard />} />
              <Route path="dashboard" element={<StudentDashboard />} />
              <Route path="attendance" element={<StudentAttendance />} />
              <Route path="timetable" element={<StudentTimetable />} />
              <Route path="assignments" element={<StudentAssignments />} />
              <Route path="projects" element={<StudentProjects />} />
              <Route path="projects/:id" element={<StudentProjectDetail />} />
              <Route path="announcements" element={<StudentAnnouncements />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="ai" element={<AIAssistant />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />

      {/* Faculty Routes */}
      <Route path="/faculty/*" element={
        <ProtectedRoute allowedRoles={['FACULTY']}>
          <Layout role="FACULTY">
            <Routes>
              <Route path="/" element={<FacultyDashboard />} />
              <Route path="dashboard" element={<FacultyDashboard />} />
              <Route path="subjects" element={<FacultySubjects />} />
              <Route path="attendance" element={<FacultyAttendance />} />
              <Route path="assignments" element={<FacultyAssignments />} />
              <Route path="marks" element={<FacultyMarks />} />
              <Route path="projects" element={<FacultyProjects />} />
              <Route path="projects/:id" element={<FacultyProjectDetail />} />
              <Route path="announcements" element={<FacultyAnnouncements />} />
              <Route path="reports" element={<FacultyReports />} />
              <Route path="timetable" element={<FacultyTimetable />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="ai" element={<AIAssistant />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </ProtectedRoute>

       } />


       {/* CR Routes */}
      <Route path="/cr/*" element={
        <ProtectedRoute allowedRoles={['CR']}>
          <Layout role="CR">
            <Routes>
              <Route path="/" element={<CRDashboard />} />
              <Route path="dashboard" element={<CRDashboard />} />
              <Route path="attendance" element={<CRAttendance />} />
              <Route path="timetable" element={<CRTimetable />} />
              <Route path="assignments" element={<CRAssignments />} />
              <Route path="announcements" element={<CRAnnouncements />} />
              <Route path="requests" element={<CRRequests />} />
              <Route path="feedback" element={<CRFeedback />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />

      {/* HOD Routes */}
      <Route path="/hod/*" element={
        <ProtectedRoute allowedRoles={['HOD']}>
          <Layout role="HOD">
            <Routes>
              <Route path="/" element={<HODDashboard />} />
              <Route path="dashboard" element={<HODDashboard />} />
              <Route path="students" element={<HODStudents />} />
              <Route path="faculty" element={<HODFaculty />} />
              <Route path="subjects" element={<HODSubjects />} />
              <Route path="attendance" element={<HODAttendance />} />
              <Route path="performance" element={<HODPerformance />} />
              <Route path="timetable" element={<HODTimetable />} />
              <Route path="announcements" element={<HODAnnouncements />} />
              <Route path="reports" element={<HODReports />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />

      {/* Admin Routes */}
      <Route path="/admin/*" element={
        <ProtectedRoute allowedRoles={['ADMIN']}>
          <Layout role="ADMIN">
            <Routes>
              <Route path="/" element={<AdminDashboard />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="students" element={<AdminStudents />} />
              <Route path="faculty" element={<AdminFaculty />} />
              <Route path="departments" element={<AdminDepartments />} />
              <Route path="courses" element={<AdminCourses />} />
              <Route path="subjects" element={<AdminSubjects />} />
              <Route path="timetable" element={<AdminTimetable />} />
              <Route path="announcements" element={<AdminAnnouncements />} />
              <Route path="reports" element={<AdminReports />} />
              <Route path="audit-logs" element={<AdminAuditLogs />} />
              <Route path="settings" element={<AdminSettings />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
