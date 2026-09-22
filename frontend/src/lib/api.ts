import { getToken } from './auth'
import {
  UserPublic,
  UserAdmin,
  TokenResponse,
  DashboardResponse,
  PaginatedResponse,
  Student,
  Faculty,
  Subject,
  SubjectAssignment,
  ClassTeacher,
  Department,
  Course,
  Semester,
  Section,
  AcademicSession,
  SystemSetting,
  CRRequest,
  Feedback,
  TimetableEntry,
  AttendanceRecord,
  AttendanceAnalytics,
  AttendancePrediction,
  Assignment,
  Submission,
  Mark,
  Project,
  ProjectMilestone,
  Announcement,
  Notification,
  AuditLog,
  SearchResult,
  SectionAttendance,
  AttendanceRoster,
  AnnouncementTargets,
  AISuggestion,
  ChatResponse,
  NotificationSummary,
} from '@/types'

const BASE_URL = `${import.meta.env.VITE_API_URL || ""}/api/v1`

class ApiClient {
  // File downloads
  downloadFile = (fileType: string, resourceId: number, filename: string) => {
    const token = getToken()
    const headers: HeadersInit = {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
    
    return fetch(`${BASE_URL}/files/${fileType}/${resourceId}/${encodeURIComponent(filename)}`, {
      headers,
    })
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const token = getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(response.status, error)
    }

    return response.json()
  }

  private async requestWithFiles<T>(
    path: string,
    formData: FormData,
    options: RequestInit = {},
  ): Promise<T> {
    const token = getToken()
    const headers: HeadersInit = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(response.status, error)
    }

    return response.json()
  }

  // Auth
  login = async (identifier: string, password: string) => {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    })
  }

  refreshToken = async (refreshToken: string) => {
    return this.request<TokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }

  logout = async (refreshToken: string) => {
    return this.request('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }

  getMe = async () => {
    return this.request<UserPublic>('/auth/me')
  }

  // Dashboard
  getDashboard = async (role: string) => {
    return this.request<DashboardResponse>(`/dashboard/${role.toLowerCase()}`)
  }

  // Students / Faculty / Subjects / Departments: see "People", "Departments"
  // and "Subjects" sections further down (params-based signatures).

  // Attendance - Student
  getMyAttendance = async () => {
    return this.request<AttendanceAnalytics>('/attendance/analytics/me')
  }

  getAttendancePredictions = async (requiredPercentage?: number) => {
    return this.request<AttendancePrediction>(
      requiredPercentage 
        ? `/attendance/predict/me?required_percentage=${requiredPercentage}`
        : '/attendance/predict/me'
    )
  }

  getAllAttendance = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<AttendanceRecord>>(
      `/attendance?page=${page}&page_size=${pageSize}`
    )
  }

  // Attendance - Faculty
  getAttendanceRoster = async (subjectId: number, section: string, date?: string) => {
    return this.request<AttendanceRoster>(
      date
        ? `/attendance/roster/${subjectId}/${section}?on_date=${date}`
        : `/attendance/roster/${subjectId}/${section}`
    )
  }

  markAttendance = async (subjectId: number, section: string, date: string, marks: Array<{student_id: number, status: string}>) => {
    return this.request<AttendanceRecord[]>('/attendance', {
      method: 'POST',
      body: JSON.stringify({
        subject_id: subjectId,
        section,
        date,
        marks,
      }),
    })
  }

  updateAttendance = async (recordId: number, status: string, note?: string) => {
    return this.request<AttendanceRecord>(`/attendance/${recordId}`, {
      method: 'PUT',
      body: JSON.stringify({ status, note }),
    })
  }

  getAttendanceBySection = async (section: string, subjectId?: number) => {
    return this.request<SectionAttendance>(
      subjectId
        ? `/attendance/analytics/section/${section}?subject_id=${subjectId}`
        : `/attendance/analytics/section/${section}`
    )
  }

  getMyAttendanceHistory = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<AttendanceRecord>>(
      `/attendance/my?page=${page}&page_size=${pageSize}`
    )
  }

  // Timetable
  getTimetable = async () => {
    return this.request<TimetableEntry[]>('/timetable/my')
  }

  getTimetableBySection = async (section: string) => {
    return this.request<TimetableEntry[]>(`/timetable/section/${section}`)
  }

  getAllTimetableEntries = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<TimetableEntry>>(
      `/timetable?page=${page}&page_size=${pageSize}`
    )
  }

  createTimetableEntry = async (data: Partial<TimetableEntry>) => {
    return this.request<TimetableEntry>('/timetable', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateTimetableEntry = async (entryId: number, data: Partial<TimetableEntry>) => {
    return this.request<TimetableEntry>(`/timetable/${entryId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteTimetableEntry = async (entryId: number) => {
    return this.request(`/timetable/${entryId}`, {
      method: 'DELETE',
    })
  }

  // Assignments - Student
  getAssignments = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Assignment>>(
      `/assignments?page=${page}&page_size=${pageSize}`
    )
  }

  getAssignment = async (id: number) => {
    return this.request<Assignment>(`/assignments/${id}`)
  }

  submitAssignment = async (assignmentId: number, textSubmission?: string, file?: File) => {
    const formData = new FormData()
    if (textSubmission) {
      formData.append('text_submission', textSubmission)
    }
    if (file) {
      formData.append('file', file)
    }
    return this.requestWithFiles<Submission>(
      `/assignments/${assignmentId}/submit`,
      formData
    )
  }

  getMySubmissions = async () => {
    // Get submissions for assignments the student is enrolled in
    return this.request<PaginatedResponse<Submission>>(`/assignments?page=1&page_size=1000`)
  }

  // Assignments - Faculty
  createAssignment = async (data: Partial<Assignment>) => {
    return this.request<Assignment>('/assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateAssignment = async (id: number, data: Partial<Assignment>) => {
    return this.request<Assignment>(`/assignments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteAssignment = async (id: number) => {
    return this.request(`/assignments/${id}`, {
      method: 'DELETE',
    })
  }

  uploadAssignmentAttachment = async (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return this.requestWithFiles<Assignment>(
      `/assignments/${id}/attachment`,
      formData
    )
  }

  getSubmissions = async (assignmentId: number, page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Submission>>(
      `/assignments/${assignmentId}/submissions?page=${page}&page_size=${pageSize}`
    )
  }

  gradeSubmission = async (submissionId: number, grade: number, feedback?: string) => {
    return this.request<Submission>(`/submissions/${submissionId}/grade`, {
      method: 'PUT',
      body: JSON.stringify({ grade, feedback }),
    })
  }

  // Marks
  getMarks = async (page: number = 1, pageSize: number = 20, subjectId?: number) => {
    return this.request<PaginatedResponse<Mark>>(
      subjectId 
        ? `/marks?page=${page}&page_size=${pageSize}&subject_id=${subjectId}`
        : `/marks?page=${page}&page_size=${pageSize}`
    )
  }

  getMyMarks = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Mark>>(
      `/marks/me?page=${page}&page_size=${pageSize}`
    )
  }

  createMark = async (data: Partial<Mark>) => {
    return this.request<Mark>('/marks', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateMark = async (id: number, data: Partial<Mark>) => {
    return this.request<Mark>(`/marks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // Projects - Student
  getMyProjects = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Project>>(
      `/projects/my?page=${page}&page_size=${pageSize}`
    )
  }

  getProject = async (id: number) => {
    return this.request<Project>(`/projects/${id}`)
  }

  joinProjectGroup = async (projectId: number, name: string, proposal?: string, memberIds: number[] = []) => {
    return this.request<Project>(`/projects/${projectId}/groups`, {
      method: 'POST',
      body: JSON.stringify({ name, proposal, member_ids: memberIds }),
    })
  }

  leaveProjectGroup = async (groupId: number) => {
    return this.request(`/projects/groups/${groupId}`, {
      method: 'DELETE',
    })
  }

  submitMilestone = async (milestoneId: number, text: string) => {
    return this.request<Project>(`/milestones/${milestoneId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ submission_text: text }),
    })
  }

  // Projects - Faculty
  createProject = async (data: Partial<Project>) => {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateProject = async (id: number, data: Partial<Project>) => {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteProject = async (id: number) => {
    return this.request(`/projects/${id}`, {
      method: 'DELETE',
    })
  }

  getSupervisedProjects = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Project>>(
      `/projects/supervised?page=${page}&page_size=${pageSize}`
    )
  }

  approveProjectGroup = async (groupId: number) => {
    return this.request<Project>(`/projects/groups/${groupId}/approve`, {
      method: 'PUT',
    })
  }

  rejectProjectGroup = async (groupId: number) => {
    return this.request<Project>(`/projects/groups/${groupId}/reject`, {
      method: 'PUT',
    })
  }

  getMilestones = async (projectId: number) => {
    return this.request<ProjectMilestone[]>(`/projects/${projectId}/milestones`)
  }

  createMilestone = async (projectId: number, title: string, description: string, deadline: string) => {
    return this.request<Project>(`/projects/${projectId}/milestones`, {
      method: 'POST',
      body: JSON.stringify({ title, description, deadline }),
    })
  }

  // Announcements
  getAnnouncements = async (params: {
    page?: number
    pageSize?: number
    q?: string
    priority?: string
    pinnedOnly?: boolean
  } = {}) => {
    const { page = 1, pageSize = 20, q, priority, pinnedOnly } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (priority) parts.push(`priority=${encodeURIComponent(priority)}`)
    if (pinnedOnly) parts.push('pinned_only=true')
    return this.request<PaginatedResponse<Announcement>>(`/announcements?${parts.join('&')}`)
  }

  getAnnouncement = async (id: number) => {
    return this.request<Announcement>(`/announcements/${id}`)
  }

  createAnnouncement = async (data: Partial<Announcement>) => {
    return this.request<Announcement>('/announcements', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateAnnouncement = async (id: number, data: Partial<Announcement>) => {
    return this.request<Announcement>(`/announcements/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteAnnouncement = async (id: number) => {
    return this.request(`/announcements/${id}`, {
      method: 'DELETE',
    })
  }

  uploadAnnouncementAttachment = async (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return this.requestWithFiles<Announcement>(
      `/announcements/${id}/attachment`,
      formData
    )
  }

  getAnnouncementTargets = async () => {
    return this.request<AnnouncementTargets>('/announcements/targets/allowed')
  }

  // Notifications
  getNotifications = async (page: number = 1, pageSize: number = 20, unreadOnly: boolean = false) => {
    return this.request<PaginatedResponse<Notification>>(
      `/notifications?page=${page}&page_size=${pageSize}${unreadOnly ? '&unread_only=true' : ''}`
    )
  }

  getNotificationSummary = async () => {
    return this.request<NotificationSummary>('/notifications/summary')
  }

  markNotificationAsRead = async (id: number) => {
    return this.request(`/notifications/${id}/read`, {
      method: 'POST',
    })
  }

  markAllNotificationsAsRead = async () => {
    return this.request('/notifications/read-all', {
      method: 'POST',
    })
  }

  deleteNotification = async (id: number) => {
    return this.request(`/notifications/${id}`, {
      method: 'DELETE',
    })
  }

  // Reports
  private async downloadReport(path: string, filename: string): Promise<void> {
    const token = getToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${BASE_URL}${path}`, { headers })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(response.status, error)
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  getAttendanceReport = async (format: 'csv' | 'pdf' = 'csv', section?: string) => {
    const params = new URLSearchParams({ format })
    if (section) params.append('section', section)
    await this.downloadReport(`/reports/attendance?${params.toString()}`, `attendance_report.${format}`)
  }

  getPerformanceReport = async (format: 'csv' | 'pdf' = 'csv') => {
    await this.downloadReport(`/reports/performance?format=${format}`, `performance_report.${format}`)
  }

  getFacultyWorkloadReport = async (format: 'csv' | 'pdf' = 'csv') => {
    await this.downloadReport(`/reports/faculty-workload?format=${format}`, `faculty_workload.${format}`)
  }

  getProjectProgressReport = async (format: 'csv' | 'pdf' = 'csv') => {
    await this.downloadReport(`/reports/project-progress?format=${format}`, `project_progress.${format}`)
  }

  getAssignmentSubmissionsReport = async (assignmentId: number, format: 'csv' | 'pdf' = 'csv') => {
    await this.downloadReport(
      `/reports/assignment-submissions?assignment_id=${assignmentId}&format=${format}`,
      `assignment_submissions.${format}`
    )
  }

  getDepartmentReport = async (departmentId?: number, format: 'csv' | 'pdf' = 'csv') => {
    const params = new URLSearchParams({ format })
    if (departmentId) params.append('department_id', String(departmentId))
    await this.downloadReport(`/reports/department?${params.toString()}`, `department_report.${format}`)
  }

  getFacultyPerformance = async (facultyId?: number, page: number = 1, pageSize: number = 20) => {
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (facultyId) parts.push(`faculty_id=${facultyId}`)
    return this.request<PaginatedResponse<{
      id: number
      name: string
      email: string
      department: string | null
      designation: string
      feedback_count: number
      average_rating: number
      feedback: { rating: number; message: string; subject_id: number | null; section: string | null; created_at: string }[]
    }>>(`/reports/faculty-performance?${parts.join('&')}`)
  }

  previewReportCsv = async (path: string): Promise<string> => {
    const token = getToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const response = await fetch(`${BASE_URL}${path}`, { headers })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(response.status, error)
    }
    return response.text()
  }

  // Search
  search = async (query: string, kind?: string, page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<SearchResult>>(
      `/search?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}${kind ? `&kind=${kind}` : ''}`
    )
  }

  // AI Assistant
  chat = async (message: string, history?: Array<{role: 'user' | 'assistant', content: string}>) => {
    const payload: Record<string, unknown> = { message }
    if (history !== undefined) {
      payload.history = history
    }
    return this.request<ChatResponse>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  getAISuggestions = async () => {
    return this.request<AISuggestion[]>('/ai/suggestions')
  }

  // Audit Logs
  getAuditLogs = async (params: {
    page?: number
    pageSize?: number
    q?: string
    userId?: number
    action?: string
    resource?: string
  } = {}) => {
    const { page = 1, pageSize = 20, q, userId, action, resource } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (userId) parts.push(`user_id=${userId}`)
    if (action) parts.push(`action=${encodeURIComponent(action)}`)
    if (resource) parts.push(`resource=${encodeURIComponent(resource)}`)
    return this.request<PaginatedResponse<AuditLog>>(`/audit-logs?${parts.join('&')}`)
  }

  getAuditActions = async () => {
    return this.request<string[]>('/audit-logs/actions')
  }

  // Users (Admin)
  getUsers = async (params: {
    page?: number
    pageSize?: number
    q?: string
    role?: string
    status?: string
  } = {}) => {
    const { page = 1, pageSize = 20, q, role, status } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (role) parts.push(`role=${encodeURIComponent(role)}`)
    if (status) parts.push(`status=${encodeURIComponent(status)}`)
    return this.request<PaginatedResponse<UserAdmin>>(`/users?${parts.join('&')}`)
  }

  getUserPermissions = async (role: string) => {
    return this.request<{ role: string; permissions: string[] }>(
      `/users/permissions?role=${encodeURIComponent(role)}`
    )
  }

  updateUser = async (id: number, data: Partial<UserAdmin>) => {
    return this.request<UserAdmin>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  suspendUser = async (id: number) => {
    return this.request(`/users/${id}/suspend`, {
      method: 'POST',
    })
  }

  activateUser = async (id: number) => {
    return this.request(`/users/${id}/activate`, {
      method: 'POST',
    })
  }

  // Students (Admin/HOD)
  getStudents = async (params: {
    page?: number
    pageSize?: number
    q?: string
    departmentId?: number
    section?: string
    semesterId?: number
  } = {}) => {
    const { page = 1, pageSize = 20, q, departmentId, section, semesterId } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (departmentId) parts.push(`department_id=${departmentId}`)
    if (section) parts.push(`section=${encodeURIComponent(section)}`)
    if (semesterId) parts.push(`semester_id=${semesterId}`)
    return this.request<PaginatedResponse<Student>>(`/students?${parts.join('&')}`)
  }

  getStudent = async (id: number) => {
    return this.request<Student>(`/students/${id}`)
  }

  createStudent = async (data: Record<string, unknown>) => {
    return this.request<Student & { initial_password?: string }>('/students', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateStudent = async (id: number, data: Record<string, unknown>) => {
    return this.request<Student>(`/students/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteStudent = async (id: number) => {
    return this.request(`/students/${id}`, {
      method: 'DELETE',
    })
  }

  // CR (Class Representative) assignment - CRs are students with extra access.
  assignCR = async (studentId: number) => {
    return this.request<Student>(`/students/${studentId}/cr`, {
      method: 'POST',
    })
  }

  removeCR = async (studentId: number) => {
    return this.request<Student>(`/students/${studentId}/cr`, {
      method: 'DELETE',
    })
  }

  getCRAssignments = async (params: {
    page?: number
    pageSize?: number
    q?: string
    departmentId?: number
    semesterId?: number
    section?: string
  } = {}) => {
    const { page = 1, pageSize = 50, q, departmentId, semesterId, section } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (departmentId) parts.push(`department_id=${departmentId}`)
    if (semesterId) parts.push(`semester_id=${semesterId}`)
    if (section) parts.push(`section=${encodeURIComponent(section)}`)
    return this.request<PaginatedResponse<Student>>(`/cr-assignments?${parts.join('&')}`)
  }

  // Faculty (Admin/HOD)
  getFaculty = async (params: {
    page?: number
    pageSize?: number
    q?: string
    departmentId?: number
  } = {}) => {
    const { page = 1, pageSize = 20, q, departmentId } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (departmentId) parts.push(`department_id=${departmentId}`)
    return this.request<PaginatedResponse<Faculty>>(`/faculty?${parts.join('&')}`)
  }

  createFaculty = async (data: Record<string, unknown>) => {
    return this.request<Faculty & { initial_password?: string }>('/faculty', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateFaculty = async (id: number, data: Record<string, unknown>) => {
    return this.request<Faculty>(`/faculty/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteFaculty = async (id: number) => {
    return this.request(`/faculty/${id}`, {
      method: 'DELETE',
    })
  }

  // Departments (Admin)
  getDepartments = async (params: { page?: number; pageSize?: number; q?: string } = {}) => {
    const { page = 1, pageSize = 50, q } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    return this.request<PaginatedResponse<Department>>(`/departments?${parts.join('&')}`)
  }

  getAllDepartments = async () => {
    return this.request<Department[]>('/departments/all')
  }

  createDepartment = async (data: Partial<Department>) => {
    return this.request<Department>('/departments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateDepartment = async (id: number, data: Partial<Department>) => {
    return this.request<Department>(`/departments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteDepartment = async (id: number) => {
    return this.request(`/departments/${id}`, {
      method: 'DELETE',
    })
  }

  assignHod = async (departmentId: number, facultyId: number) => {
    return this.request<Department>(`/departments/${departmentId}/hod?faculty_id=${facultyId}`, {
      method: 'PUT',
    })
  }

  // Courses & semesters & sections (Admin)
  getCourses = async (params: { page?: number; pageSize?: number; q?: string; departmentId?: number } = {}) => {
    const { page = 1, pageSize = 50, q, departmentId } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (departmentId) parts.push(`department_id=${departmentId}`)
    return this.request<PaginatedResponse<Course>>(`/courses?${parts.join('&')}`)
  }

  createCourse = async (data: Partial<Course>) => {
    return this.request<Course>('/courses', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateCourse = async (id: number, data: Partial<Course>) => {
    return this.request<Course>(`/courses/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteCourse = async (id: number) => {
    return this.request(`/courses/${id}`, {
      method: 'DELETE',
    })
  }

  getSemesters = async (courseId?: number) => {
    return this.request<Semester[]>(
      courseId ? `/semesters?course_id=${courseId}` : '/semesters'
    )
  }

  getSections = async (params: { page?: number; pageSize?: number; q?: string; isActive?: boolean } = {}) => {
    const { page = 1, pageSize = 50, q, isActive } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (isActive !== undefined) parts.push(`is_active=${isActive}`)
    return this.request<PaginatedResponse<Section>>(`/sections?${parts.join('&')}`)
  }

  getAllSections = async () => {
    return this.request<Section[]>('/sections/all')
  }

  createSection = async (data: Partial<Section>) => {
    return this.request<Section>('/sections', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateSection = async (id: number, data: Partial<Section>) => {
    return this.request<Section>(`/sections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteSection = async (id: number) => {
    return this.request(`/sections/${id}`, {
      method: 'DELETE',
    })
  }

  getAcademicSessions = async () => {
    return this.request<AcademicSession[]>('/academic-sessions')
  }

  // Subjects (Admin/HOD)
  getMySubjects = async () => {
    return this.request<Subject[]>('/subjects/my')
  }

  getSubjects = async (params: {
    page?: number
    pageSize?: number
    q?: string
    departmentId?: number
    semesterId?: number
  } = {}) => {
    const { page = 1, pageSize = 50, q, departmentId, semesterId } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (q) parts.push(`q=${encodeURIComponent(q)}`)
    if (departmentId) parts.push(`department_id=${departmentId}`)
    if (semesterId) parts.push(`semester_id=${semesterId}`)
    return this.request<PaginatedResponse<Subject>>(`/subjects?${parts.join('&')}`)
  }

  getAllSubjects = async (departmentId?: number) => {
    return this.request<Subject[]>(
      departmentId ? `/subjects/all?department_id=${departmentId}` : '/subjects/all'
    )
  }

  createSubject = async (data: Partial<Subject>) => {
    return this.request<Subject>('/subjects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateSubject = async (id: number, data: Partial<Subject>) => {
    return this.request<Subject>(`/subjects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteSubject = async (id: number) => {
    return this.request(`/subjects/${id}`, {
      method: 'DELETE',
    })
  }

  getSubjectAssignments = async (params: {
    page?: number
    pageSize?: number
    facultyId?: number
    section?: string
    subjectId?: number
  } = {}) => {
    const { page = 1, pageSize = 50, facultyId, section, subjectId } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (facultyId) parts.push(`faculty_id=${facultyId}`)
    if (section) parts.push(`section=${encodeURIComponent(section)}`)
    if (subjectId) parts.push(`subject_id=${subjectId}`)
    return this.request<PaginatedResponse<SubjectAssignment>>(`/subjects/assignments?${parts.join('&')}`)
  }

  createSubjectAssignment = async (data: Partial<SubjectAssignment>) => {
    return this.request<SubjectAssignment>('/subjects/assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

   deleteSubjectAssignment = async (id: number) => {
    return this.request(`/subjects/assignments/${id}`, {
      method: 'DELETE',
    })
  }

  // Class teachers
  getClassTeachers = async (params: { section?: string; semesterId?: number } = {}) => {
    const { section, semesterId } = params
    const parts: string[] = []
    if (section) parts.push(`section=${encodeURIComponent(section)}`)
    if (semesterId) parts.push(`semester_id=${semesterId}`)
    return this.request<ClassTeacher[]>(`/class-teachers${parts.length ? `?${parts.join('&')}` : ''}`)
  }

  createClassTeacher = async (data: Partial<ClassTeacher>) => {
    return this.request<ClassTeacher>('/class-teachers', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  deleteClassTeacher = async (id: number) => {
    return this.request(`/class-teachers/${id}`, {
      method: 'DELETE',
    })
  }

  // Settings
  getSettings = async () => {
    return this.request<SystemSetting[]>('/settings')
  }

  updateSetting = async (key: string, value: string) => {
    return this.request<SystemSetting>(`/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    })
  }

  // CR requests
  getCRRequests = async (params: { page?: number; pageSize?: number; status?: string } = {}) => {
    const { page = 1, pageSize = 20, status } = params
    const parts = [`page=${page}`, `page_size=${pageSize}`]
    if (status) parts.push(`status=${encodeURIComponent(status)}`)
    return this.request<PaginatedResponse<CRRequest>>(`/cr/requests?${parts.join('&')}`)
  }

  createCRRequest = async (data: { request_type: string; title: string; description: string; section?: string }) => {
    return this.request<CRRequest>('/cr/requests', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  resolveCRRequest = async (id: number, status: string, resolutionNote?: string) => {
    return this.request<CRRequest>(`/cr/requests/${id}/resolve`, {
      method: 'PUT',
      body: JSON.stringify({ status, resolution_note: resolutionNote }),
    })
  }

  // Feedback
  getFeedback = async (page: number = 1, pageSize: number = 20) => {
    return this.request<PaginatedResponse<Feedback>>(
      `/feedback?page=${page}&page_size=${pageSize}`
    )
  }

  submitFeedback = async (data: {
    target_type: string
    subject_id?: number
    department_id?: number
    section?: string
    rating: number
    message: string
  }) => {
    return this.request('/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Attendance analytics
  getStudentAnalytics = async (studentId: number) => {
    return this.request<AttendanceAnalytics>(`/attendance/analytics/student/${studentId}`)
  }
}

class ApiError extends Error {
  constructor(public status: number, public data: Record<string, unknown>) {
    super(`HTTP ${status}`)
  }
}

/**
 * Extract a human-readable message from an API error.
 *
 * The backend always returns {"success": false, "message": "...", "error_code": "..."}.
 */
export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error instanceof ApiError) {
    const message = error.data?.message
    if (typeof message === 'string' && message) return message
    const detail = error.data?.detail
    if (typeof detail === 'string' && detail) return detail
    if (error.status === 401) return 'Your session has expired. Please log in again.'
    if (error.status === 403) return 'You are not allowed to perform this action.'
    if (error.status === 404) return 'The requested resource was not found.'
  }
  if (error instanceof Error) return error.message
  return fallback
}

export const api = new ApiClient()

export function downloadFile(
  fileType: string,
  resourceId: number,
  filename: string
): Promise<Response> {
  const token = getToken()
  const headers: HeadersInit = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  
  return fetch(`${BASE_URL}/files/${fileType}/${resourceId}/${encodeURIComponent(filename)}`, {
    headers,
  })
}

