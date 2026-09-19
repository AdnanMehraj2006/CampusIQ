import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Course, Department } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
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
import { Plus, Edit2, Trash2, BookOpen, Search } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AdminCourses() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [editing, setEditing] = useState<Course | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState<Course | null>(null)

  const { data: departments } = useQuery<Department[]>({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-courses', departmentId],
    queryFn: () => api.getCourses({ pageSize: 100, departmentId: Number(departmentId) || undefined }),
  })

  const createMutation = useMutation({
    mutationFn: (payload: Partial<Course>) => api.createCourse(payload),
    onSuccess: () => {
      toast.success('Course created')
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] })
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to create course')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Course> }) => api.updateCourse(id, payload),
    onSuccess: () => {
      toast.success('Course updated')
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] })
      setFormOpen(false)
      setEditing(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to update course')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteCourse(id),
    onSuccess: () => {
      toast.success('Course deleted')
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] })
      setDeleting(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to delete course')),
  })

  const courses = (data?.items || []).filter((c) =>
    `${c.name} ${c.code}`.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Courses"
        subtitle="Degree programmes offered by departments"
        actions={
          <Button
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Course
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search courses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} className="sm:w-56">
          <option value="">All departments</option>
          {(departments || []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
      </div>

      {isLoading ? (
        <LoadingState message="Loading courses..." />
      ) : isError ? (
        <ErrorState message="Failed to load courses" onRetry={refetch} />
      ) : courses.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={BookOpen} title="No courses found" message="Create your first course to get started." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Students</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {courses.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-mono text-xs">{c.code}</TableCell>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.department_name || '-'}</TableCell>
                  <TableCell>{c.duration_years} year(s)</TableCell>
                  <TableCell>{c.student_count ?? 0}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setEditing(c)
                          setFormOpen(true)
                        }}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit course"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(c)}
                        className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        aria-label="Delete course"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableWrapper>
      )}

      <CourseForm
        key={editing?.id ?? 'new'}
        open={formOpen}
        course={editing}
        departments={departments || []}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={(payload) =>
          editing ? updateMutation.mutate({ id: editing.id, payload }) : createMutation.mutate(payload)
        }
        submitting={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Delete course"
        message={
          <>
            Are you sure you want to delete <strong>{deleting?.code} - {deleting?.name}</strong>?
          </>
        }
        confirmLabel="Delete"
        destructive
      />
    </div>
  )
}

function CourseForm({
  open,
  course,
  departments,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  course: Course | null
  departments: Department[]
  onClose: () => void
  onSubmit: (payload: Partial<Course>) => void
  submitting: boolean
}) {
  const [name, setName] = useState(course?.name ?? '')
  const [code, setCode] = useState(course?.code ?? '')
  const [durationYears, setDurationYears] = useState(String(course?.duration_years ?? 4))
  const [departmentId, setDepartmentId] = useState(String(course?.department_id ?? ''))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={course ? 'Edit course' : 'New course'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                name,
                code,
                duration_years: Number(durationYears) || 4,
                department_id: Number(departmentId) || undefined,
              })
            }
            disabled={submitting || !name || !code || !departmentId}
          >
            {course ? 'Save changes' : 'Create'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Code" required>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. BTECH-CSE" />
        </Field>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. B.Tech Computer Science" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Duration (years)" required>
            <Input
              type="number"
              min={1}
              max={8}
              value={durationYears}
              onChange={(e) => setDurationYears(e.target.value)}
            />
          </Field>
          <Field label="Department" required>
            <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
              <option value="">Select department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>
    </Modal>
  )
}