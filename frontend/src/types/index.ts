export type Role = 'ADMIN' | 'HOD' | 'FACULTY' | 'CR' | 'STUDENT'

export interface UserPublic {
  id: number
  college_id: string
  name: string
  email: string
  phone?: string | null
  role: Role
  status: string
  avatar_url?: string | null
  last_login_at?: string | null
}

export interface TokenResponse {
  success: boolean
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserPublic
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export interface Student {
  id: number
  user_id: number
  enrollment_number: string
  department_id: number
  course_id?: number | null
  admission_year: number
  guardian_name?: string | null
  guardian_phone?: string | null
  name: string
  email: string
  phone?: string | null
  role: Role
  status: string
  college_id: string
  department_name?: string | null
  course_name?: string | null
  attendance_percentage?: number | null
}

export interface Faculty {
  id: number
  user_id: number
  department_id: number
  designation: string
  specialization?: string | null
  name: string
  email: string
  phone?: string | null
  role: Role
  status: string
  college_id: string
  department_name?: string | null
  subject_count?: number | null
  is_hod?: boolean | null
}

export interface Subject {
  id: number
  code: string
  name: string
  credits: number
  department_id: number
  weekly_periods?: number
  department_name?: string | null
}

export interface SubjectAssignment {
  id: number
  subject_id: number
  faculty_id: number
  section: string
  subject_name?: string | null
  subject_code?: string | null
  faculty_name?: string | null
}

export interface ClassTeacher {
  id: number
  faculty_id: number
  section: string
  faculty_name?: string | null
}

export interface Department {
  id: number
  name: string
  code: string
  description?: string | null
  hod_id?: number | null
  hod_name?: string | null
  student_count?: number
  faculty_count?: number
}

export interface Course {
  id: number
  name: string
  code: string
  department_id: number
  duration_years: number
  description?: string | null
  department_name?: string | null
  student_count?: number
}

export interface AcademicSession {
  id: number
  name: string
  start_date?: string | null
  end_date?: string | null
  is_active: boolean
}

export interface Classroom {
  id: number
  room_number: string
  building?: string | null
  capacity?: number | null
  type?: string | null
}

export interface SystemSetting {
  id: number
  key: string
  value: string
  description?: string | null
  category: string
}

export interface CRRequest {
  id: number
  submitted_by: number
  request_type: string
  title: string
  description: string
  status: string
  resolution_note?: string | null
  section?: string | null
  author_name?: string | null
  created_at: string
}

export interface Feedback {
  id: number
  submitted_by: number
  target_type: string
  subject_id?: number | null
  department_id?: number | null
  section?: string | null
  rating: number
  message: string
  status: string
  response?: string | null
  author_name?: string | null
  subject_name?: string | null
  created_at: string
}

export interface UserAdmin {
  id: number
  college_id: string
  name: string
  email: string
  phone?: string | null
  role: Role
  status: string
  avatar_url?: string | null
  last_login_at?: string | null
  created_at?: string | null
  must_change_password?: boolean
}

export interface TimetableEntry {
  id: number
  day: string
  period: number
  start_time: string
  end_time: string
  subject_id: number
  faculty_id: number
  classroom_id: number
  section: string
  subject_name?: string
  subject_code?: string
  faculty_name?: string
  room_number?: string
}

export interface AttendanceRecord {
  id: number
  student_id: number
  subject_id: number
  date: string
  status: 'present' | 'absent' | 'late' | 'excused'
  marked_by: number
  note?: string
  student_name?: string
  enrollment_number?: string
  subject_name?: string
  subject_code?: string
  section?: string
}

export interface AttendanceAnalytics {
  total_classes: number
  attended: number
  absent: number
  late: number
  excused: number
  overall_percentage: number
  required_percentage: number
  zone: 'safe' | 'warning' | 'critical' | 'none'
  classes_attended: number
  classes_conducted: number
  classes_missed: number
  subject_wise: Array<{
    subject_id: number
    subject_name: string
    subject_code: string
    classes_attended: number
    classes_conducted: number
    percentage: number
    zone: string
  }>
  trend: Array<{
    date: string
    percentage: number
    conducted: number
    attended: number
  }>
}

export interface AttendancePrediction {
  current_percentage: number
  required_percentage: number
  classes_needed_to_pass: number
  prediction: string
}

export interface Assignment {
  id: number
  title: string
  description?: string
  instructions?: string
  subject_id: number
  subject_name?: string
  subject_code?: string
  faculty_id: number
  faculty_name?: string
  section?: string
  deadline: string
  max_marks: number
  attachment_path?: string
  attachment_name?: string
  allow_late: boolean
  is_published: boolean
  created_at: string
  submission_count?: number
  my_submission?: {
    id: number
    submitted_at: string
    is_late: boolean
    grade?: number
    feedback?: string
    file_name?: string
  }
}

export interface Submission {
  id: number
  assignment_id: number
  student_id: number
  file_name?: string
  text_submission?: string
  submitted_at: string
  is_late: boolean
  grade?: number
  feedback?: string
  graded_at?: string
  student_name?: string
  enrollment_number?: string
  assignment_title?: string
  max_marks?: number
}

export interface Mark {
  id: number
  student_id: number
  subject_id: number
  assessment_type: string
  title: string
  marks: number
  max_marks: number
  remarks?: string
  percentage: number
  subject_name?: string
  student_name?: string
  entered_at: string
}

export interface Project {
  id: number
  title: string
  description?: string
  project_code: string
  department_id: number
  semester_id?: number
  supervisor_id: number
  status: string
  deadline?: string
  max_group_size: number
  created_at: string
  supervisor_name?: string
  department_name?: string
  group_count?: number
  member_names?: string[]
  progress_percentage?: number
  my_group_id?: number
}

export interface ProjectMilestone {
  id: number
  project_id: number
  title: string
  description?: string
  status: string
  order_index: number
  deadline?: string
  submission_text?: string
  submitted_at?: string
  feedback?: string
  reviewed_at?: string
  project_title?: string
  is_overdue?: boolean
}

export interface Announcement {
  id: number
  title: string
  content: string
  summary?: string
  target_type: string
  department_id?: number
  course_id?: number
  semester_id?: number
  section?: string
  priority: string
  published_by: number
  attachment_path?: string
  attachment_name?: string
  published_at: string
  expiry_at?: string
  is_pinned: boolean
  author_name?: string
  author_role?: string
}

export interface Notification {
  id: number
  type: string
  title: string
  message: string
  is_read: boolean
  resource_type?: string
  resource_id?: number
  created_at: string
}

export interface NotificationSummary {
  unread_count: number
  total: number
  by_type: Record<string, number>
}

export interface AuditLog {
  id: number
  user_id: number | null
  user_name: string | null
  role: string | null
  action: string
  resource: string
  resource_id?: string | number | null
  ip_address?: string | null
  details?: Record<string, unknown> | null
  created_at: string | null
}

export interface SearchResult {
  type: string
  id: number
  title: string
  subtitle: string
  meta: Record<string, unknown>
}

export interface SectionAttendanceStudent {
  id: number
  name: string
  percentage: number
  zone: string
}

export interface SectionAttendance {
  section?: string
  overall?: number
  conducted?: number
  attended?: number
  students?: SectionAttendanceStudent[]
}

export type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused'

export interface AttendanceRosterStudent {
  student_id: number
  name: string
  enrollment_number: string
  status: AttendanceStatus | null
}

export interface AttendanceRoster {
  subject_id: number
  section: string
  date: string | null
  already_marked: boolean
  students: AttendanceRosterStudent[]
}

export interface AnnouncementTargets {
  targets: string[]
  sections: string[]
}

export interface AISuggestion {
  question: string
  category: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  tools_used?: string[]
  mode?: string
}

export interface DashboardResponse {
  success: boolean
  role: string
  user: UserPublic
  cards: Array<{
    label: string
    value: string | number
    sublabel?: string
    trend?: string
  }>
  attendance?: AttendanceAnalytics
  today_classes?: Array<{
    period: number
    subject: string
    faculty: string
    room: string
    time: string
  }>
  upcoming_assignments?: Array<{
    id: number
    title: string
    subject: string
    deadline: string
    max_marks: number
    submitted: boolean
    days_left?: number
  }>
  upcoming_exams?: Array<{
    id: number
    title: string
    subject: string
    type: string
    max_marks: number
  }>
  projects?: Array<{
    id: number
    title: string
    status: string
    progress: number
    deadline?: string
  }>
  recent_marks?: Array<{
    id: number
    title: string
    subject: string
    marks: number
    max_marks: number
  }>
  announcements?: Array<{
    id: number
    title: string
    priority: string
    published_at: string
  }>
  section?: string
  semester_number?: number
  department_name?: string
  subjects?: Array<{
    id: number
    name: string
    code?: string
    credits?: number
  }>
  sections?: string[]
  class_overview?: {
    section?: string
    overall?: number
    conducted?: number
    attended?: number
    students?: Array<{
      id: number
      name: string
      percentage: number
      zone: string
    }>
  }
  timetable?: Array<{
    day: string
    period: number
    subject?: string
    faculty?: string
  }>
  my_requests?: Array<{
    id: number
    title: string
    type: string
    status: string
    created_at: string
  }>
  active_session?: {
    id: number
    name: string
  }
  charts?: {
    attendance_zones?: Array<{
      name: string
      value: number
    }>
    students_by_department?: Array<{
      name: string
      students: number
      faculty: number
    }>
  }
  unread_notifications?: number
}
