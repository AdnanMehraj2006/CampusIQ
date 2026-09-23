import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Course, Semester, Section, Department } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
import { Field } from '@/components/ui/page-header'
import { Badge } from '@/components/ui/badge'
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
import { Plus, Edit2, Trash2, Layers, Search } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function HODAcademic() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<Section | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState<Section | null>(null)
  const [departmentId, setDepartmentId] = useState('')
  const [courseId, setCourseId] = useState('')

  const { data: departments } = useQuery({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const { data: courses } = useQuery({
    queryKey: ['hod-academic-courses', departmentId],
    queryFn: () => api.getCourses({ pageSize: 100, departmentId: departmentId ? Number(departmentId) : undefined }),
    enabled: departmentId !== '',
  })

  const { data: semesters } = useQuery({
    queryKey: ['hod-academic-semesters', courseId],
    queryFn: () => api.getSemesters(courseId ? Number(courseId) : undefined),
    enabled: courseId !== '',
  })

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-academic-sections', departmentId, courseId],
    queryFn: () => api.getSections({ 
      pageSize: 100, 
      departmentId: departmentId ? Number(departmentId) : undefined,
      courseId: courseId ? Number(courseId) : undefined 
    }),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['hod-academic-sections'] })
  }

  const createMutation = useMutation({
    mutationFn: (payload: Partial<Section>) => api.createSection(payload),
    onSuccess: () => {
      toast.success('Section created')
      refresh()
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to create section')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Section> }) =>
      api.updateSection(id, payload),
    onSuccess: () => {
      toast.success('Section updated')
      refresh()
      setFormOpen(false)
      setEditing(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to update section')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteSection(id),
    onSuccess: () => {
      toast.success('Section deleted')
      refresh()
      setDeleting(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to delete section')),
  })

  const sections = (data?.items || []).filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Academic Management"
        subtitle="Manage courses, semesters, and sections for your department"
      />

      <div className="flex gap-3 items-center">
        <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} className="sm:w-40">
          <option value="">Select department</option>
          {(departments || []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
        <Select value={courseId} onChange={(e) => setCourseId(e.target.value)} className="sm:w-40">
          <option value="">All courses</option>
          {(courses?.items || []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search sections..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 sm:max-w-sm"
          />
        </div>
        <Button onClick={() => {
          setEditing(null)
          setFormOpen(true)
        }}>
          <Plus className="mr-2 h-4 w-4" />
          New Section
        </Button>
      </div>

      {isLoading ? (
        <LoadingState message="Loading academic data..." />
      ) : isError ? (
        <ErrorState message="Failed to load academic data" onRetry={refetch} />
      ) : sections.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={Layers} title="No sections found" message="Create sections for your department's courses." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Course</TableHead>
                <TableHead>Semester</TableHead>
                <TableHead>Students</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sections.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell className="text-gray-500 dark:text-gray-400">
                    {s.course_name ?? '-'}
                  </TableCell>
                  <TableCell className="text-gray-500 dark:text-gray-400">
                    {s.semester_number ? `Semester ${s.semester_number}` : '-'}
                  </TableCell>
                  <TableCell>{s.student_count ?? 0}</TableCell>
                  <TableCell>
                    {s.is_active ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="danger">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setEditing(s)
                          setFormOpen(true)
                        }}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit section"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(s)}
                        className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        aria-label="Delete section"
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

      <SectionForm
        key={editing?.id ?? 'new'}
        open={formOpen}
        section={editing}
        departments={departments || []}
        courses={courses?.items || []}
        semesters={semesters || []}
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
        title="Delete section"
        message={
          <>
            Are you sure you want to delete section <strong>{deleting?.name}</strong>? Sections still
            referenced by students or academic records cannot be deleted - deactivate them instead.
          </>
        }
        confirmLabel="Delete"
        destructive
      />
    </div>
  )
}

function SectionForm({
  open,
  section,
  departments,
  courses,
  semesters,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  section: Section | null
  departments: Department[]
  courses: Course[]
  semesters: Semester[]
  onClose: () => void
  onSubmit: (payload: Partial<Section>) => void
  submitting: boolean
}) {
  const [name, setName] = useState(section?.name ?? '')
  const [description, setDescription] = useState(section?.description ?? '')
  const [isActive, setIsActive] = useState(section?.is_active ?? true)
  const [departmentId, setDepartmentId] = useState(section?.course_id ? '' : '')
  const [courseId, setCourseId] = useState(section?.course_id?.toString() ?? '')
  const [semesterId, setSemesterId] = useState(section?.semester_id?.toString() ?? '')

  const handleDepartmentChange = (val: string) => {
    setDepartmentId(val)
    setCourseId('')
    setSemesterId('')
  }

  const handleCourseChange = (val: string) => {
    setCourseId(val)
    setSemesterId('')
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={section ? 'Edit section' : 'New section'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({ 
              name: name.trim(), 
              description: description.trim() || undefined, 
              is_active: isActive,
              course_id: courseId ? Number(courseId) : undefined,
              semester_id: semesterId ? Number(semesterId) : undefined,
            })}
            disabled={submitting || !name.trim() || !courseId || !semesterId}
          >
            {section ? 'Save changes' : 'Create'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. A" maxLength={10} />
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
          <Field label="Course" required>
            <Select value={courseId} onChange={(e) => handleCourseChange(e.target.value)}>
              <option value="">Select course</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {courseId && (
          <Field label="Semester" required>
            <Select value={semesterId} onChange={(e) => setSemesterId(e.target.value)}>
              <option value="">Select semester</option>
              {semesters.map((s) => (
                <option key={s.id} value={s.id}>
                  Semester {s.semester_number}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label="Description">
          <Textarea
            value={description ?? ''}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional notes about this section"
            rows={3}
          />
        </Field>
        <Field label="Status">
          <Select value={isActive ? 'active' : 'inactive'} onChange={(e) => setIsActive(e.target.value === 'active')}>
            <option value="active">Active (available in selectors)</option>
            <option value="inactive">Inactive (hidden from new selectors)</option>
          </Select>
        </Field>
      </div>
    </Modal>
  )
}
