import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Student, Department, Course, Semester } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
import { CredentialsModal, CreatedCredentials } from '@/components/ui/credentials-modal'
import { Field } from '@/components/ui/page-header'
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Search, ChevronLeft, ChevronRight, GraduationCap, Plus, Edit2, ShieldBan, ShieldCheck, UserCheck, UserX } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AdminStudents() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [section, setSection] = useState('')
  const [editing, setEditing] = useState<Student | null>(null)
  const [deactivating, setDeactivating] = useState<Student | null>(null)
  const [credentials, setCredentials] = useState<CreatedCredentials | null>(null)
  const [crRemoving, setCrRemoving] = useState<Student | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-students', page, search, departmentId, section],
    queryFn: () =>
      api.getStudents({ page, pageSize: 15, q: search || undefined, departmentId: departmentId ? Number(departmentId) : undefined, section: section || undefined }),
  })

  const { data: departments } = useQuery({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const { data: courses } = useQuery({
    queryKey: ['form-courses', departmentId],
    queryFn: () => api.getCourses({ departmentId: departmentId ? Number(departmentId) : undefined }),
    enabled: departmentId !== '',
  })

  const { data: semesters } = useQuery({
    queryKey: ['form-semesters'],
    queryFn: () => api.getSemesters(),
  })

  const { data: sectionsData } = useQuery({
    queryKey: ['all-sections'],
    queryFn: () => api.getAllSections(),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-students'] })
    queryClient.invalidateQueries({ queryKey: ['all-sections'] })
  }

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteStudent(id),
    onSuccess: () => {
      toast.success('Student deleted')
      refresh()
      setDeactivating(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to delete student'))
    },
  })

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.createStudent(payload),
    onSuccess: (created) => {
      toast.success('Student created')
      refresh()
      setEditing(null)
      // Surface the auto-generated password exactly once.
      if (created?.initial_password) {
        setCredentials({
          name: created.name,
          identifier: created.email,
          password: created.initial_password,
        })
      }
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to create student'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      api.updateStudent(id, payload),
    onSuccess: () => {
      toast.success('Student updated')
      refresh()
      setEditing(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to update student'))
    },
  })

  const assignCRMutation = useMutation({
    mutationFn: (id: number) => api.assignCR(id),
    onSuccess: () => {
      toast.success('Student appointed as CR')
      refresh()
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to assign CR'))
    },
  })

  const removeCRMutation = useMutation({
    mutationFn: (id: number) => api.removeCR(id),
    onSuccess: () => {
      toast.success('CR status removed')
      refresh()
      setCrRemoving(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to remove CR'))
    },
  })

  const students = data?.items || []
  const pagination = data?.pagination
  const sections = sectionsData?.map((s) => s.name) || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Management"
        subtitle="Create, edit, and manage student records"
      />

      <Card>
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Search by name, email or enrollment..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              className="pl-9"
            />
          </div>
          <Select value={departmentId} onChange={(e) => { setDepartmentId(e.target.value); setPage(1) }} className="sm:w-40">
            <option value="">All departments</option>
            {departments?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
          <Select value={section} onChange={(e) => { setSection(e.target.value); setPage(1) }} className="sm:w-40">
            <option value="">All sections</option>
            {sections.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <Button onClick={() => setEditing({} as Student)} className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Student
          </Button>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading students..." />
      ) : isError ? (
        <ErrorState message="Failed to load students" onRetry={refetch} />
      ) : students.length === 0 ? (
        <Card>
          <EmptyState icon={GraduationCap} title="No students found" message="Try adjusting your search or filters." />
        </Card>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Student</TableHead>
                <TableHead>Enrollment</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Section</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {students.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{s.email}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{s.enrollment_number}</TableCell>
                  <TableCell>{s.department_name ?? '-'}</TableCell>
                  <TableCell>{s.section}</TableCell>
                  <TableCell>
                    <Badge variant={s.role === 'CR' ? 'warning' : 'info'}>
                      {s.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {s.status === 'active' ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="danger">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(s)}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit student"
                        title="Edit student"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      {s.role === 'CR' ? (
                        <button
                          onClick={() => setCrRemoving(s)}
                          className="rounded-lg p-1.5 text-amber-600 transition-colors hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-900/20"
                          aria-label="Remove CR"
                          title="Remove CR status"
                        >
                          <UserX className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => assignCRMutation.mutate(s.id)}
                          disabled={assignCRMutation.isPending}
                          className="rounded-lg p-1.5 text-green-600 transition-colors hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                          aria-label="Appoint as CR"
                          title="Appoint as Class Representative"
                        >
                          <UserCheck className="h-4 w-4" />
                        </button>
                      )}
                      {s.status === 'active' ? (
                        <button
                          onClick={() => setDeactivating(s)}
                          className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                          aria-label="Deactivate student"
                          title="Delete student"
                        >
                          <ShieldBan className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            api.updateStudent(s.id, { status: 'active' })
                            toast.success('Student reactivated')
                            refresh()
                          }}
                          className="rounded-lg p-1.5 text-green-600 transition-colors hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                          aria-label="Activate student"
                          title="Activate student"
                        >
                          <ShieldCheck className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableWrapper>
      )}

      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 pt-4 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Page {pagination.page} of {pagination.total_pages} · {pagination.total} students
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={pagination.page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
              disabled={pagination.page >= pagination.total_pages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <StudentModal
        key={editing?.id ?? 'closed'}
        student={editing}
        departments={departments || []}
        courses={courses?.items || []}
        semesters={semesters || []}
        sections={sections}
        submitting={createMutation.isPending || updateMutation.isPending}
        onClose={() => setEditing(null)}
        onSubmit={(payload) => {
          if (editing) {
            updateMutation.mutate({ id: editing.id, payload })
          } else {
            createMutation.mutate(payload)
          }
        }}
      />

      <ConfirmDialog
        open={!!deactivating}
        onClose={() => setDeactivating(null)}
        onConfirm={() => deactivating && deleteMutation.mutate(deactivating.id)}
        title="Delete student"
        message={
          <>
            Are you sure you want to delete <strong>{deactivating?.name}</strong>? This action cannot be
            undone and will also remove their associated user account.
          </>
        }
        confirmLabel="Delete"
        destructive
      />

      <ConfirmDialog
        open={!!crRemoving}
        onClose={() => setCrRemoving(null)}
        onConfirm={() => crRemoving && removeCRMutation.mutate(crRemoving.id)}
        title="Remove CR status"
        message={
          <>
            Remove <strong>{crRemoving?.name}</strong> as Class Representative? The account keeps
            working as a normal student.
          </>
        }
        confirmLabel="Remove CR"
        destructive
      />

      <CredentialsModal credentials={credentials} onClose={() => setCredentials(null)} />
    </div>
  )
}

function StudentModal({
  student,
  departments,
  courses,
  semesters,
  sections,
  submitting,
  onClose,
  onSubmit,
}: {
  student: Student | null
  departments: Department[]
  courses: Course[]
  semesters: Semester[]
  sections: string[]
  submitting?: boolean
  onClose: () => void
  onSubmit: (payload: Record<string, unknown>) => void
}) {
  const [name, setName] = useState(student?.name ?? '')
  const [email, setEmail] = useState(student?.email ?? '')
  const [enrollmentNumber, setEnrollmentNumber] = useState(student?.enrollment_number ?? '')
  const [departmentId, setDepartmentId] = useState(student?.department_id?.toString() ?? '')
  const [courseId, setCourseId] = useState(student?.course_id?.toString() ?? '')
  const [semesterId, setSemesterId] = useState(student?.semester_id?.toString() ?? '')
  const [section, setSection] = useState(student?.section ?? '')
  const [admissionYear, setAdmissionYear] = useState(student?.admission_year?.toString() ?? '')
  const [collegeId, setCollegeId] = useState(student?.college_id ?? '')

  const handleDepartmentChange = (val: string) => {
    setDepartmentId(val)
    setCourseId('')
    setSemesterId('')
  }

  const handleCourseChange = (val: string) => {
    setCourseId(val)
    setSemesterId('')
  }

  const canSubmit = name.trim() && email.trim() && enrollmentNumber.trim() && departmentId && section && admissionYear

  return (
    <Modal
      open={student !== null}
      onClose={onClose}
      title={student ? 'Edit student' : 'Add student'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({
              name: name.trim(),
              email: email.trim(),
              enrollment_number: enrollmentNumber.trim(),
              department_id: Number(departmentId),
              course_id: courseId ? Number(courseId) : undefined,
              semester_id: semesterId ? Number(semesterId) : undefined,
              section,
              admission_year: Number(admissionYear),
              college_id: collegeId.trim() || undefined,
            })}
            disabled={!canSubmit || submitting}
          >
            {student ? 'Save changes' : 'Create student'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Full name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Email" required>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Enrollment number" required>
          <Input value={enrollmentNumber} onChange={(e) => setEnrollmentNumber(e.target.value)} />
        </Field>
        <Field label="College ID">
          <Input value={collegeId} onChange={(e) => setCollegeId(e.target.value)} placeholder="Leave blank to auto-generate" />
        </Field>
        <Field label="Department" required>
          <Select value={departmentId} onChange={(e) => handleDepartmentChange(e.target.value)}>
            <option value="">Select department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
        </Field>
        {departmentId && (
          <Field label="Course">
            <Select value={courseId} onChange={(e) => handleCourseChange(e.target.value)}>
              <option value="">All courses</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label="Semester">
          <Select value={semesterId} onChange={(e) => setSemesterId(e.target.value)}>
            <option value="">All semesters</option>
            {semesters.map((s) => (
              <option key={s.id} value={s.id}>
                Semester {s.semester_number}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Section" required>
          <Select value={section} onChange={(e) => setSection(e.target.value)}>
            <option value="">Select section</option>
            {sections.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Admission year" required>
          <Input type="number" value={admissionYear} onChange={(e) => setAdmissionYear(e.target.value)} min={2000} max={2100} />
        </Field>
        {!student && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            A secure temporary password is generated automatically and shown once after creation.
          </p>
        )}
      </div>
    </Modal>
  )
}
