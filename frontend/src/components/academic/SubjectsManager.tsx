import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Subject, Department } from '@/types'
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

export function SubjectsManager() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [editing, setEditing] = useState<Subject | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState<Subject | null>(null)

  const { data: departments } = useQuery<Department[]>({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-subjects', departmentId],
    queryFn: () =>
      api.getSubjects({ pageSize: 100, departmentId: Number(departmentId) || undefined }),
  })

  const createMutation = useMutation({
    mutationFn: (payload: Partial<Subject>) => api.createSubject(payload),
    onSuccess: () => {
      toast.success('Subject created')
      queryClient.invalidateQueries({ queryKey: ['admin-subjects'] })
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to create subject')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Subject> }) => api.updateSubject(id, payload),
    onSuccess: () => {
      toast.success('Subject updated')
      queryClient.invalidateQueries({ queryKey: ['admin-subjects'] })
      setFormOpen(false)
      setEditing(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to update subject')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteSubject(id),
    onSuccess: () => {
      toast.success('Subject deleted')
      queryClient.invalidateQueries({ queryKey: ['admin-subjects'] })
      setDeleting(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to delete subject')),
  })

  const subjects = (data?.items || []).filter((s) =>
    `${s.name} ${s.code}`.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subjects"
        subtitle="Manage subjects offered by each department"
        actions={
          <Button
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Subject
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search subjects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          value={departmentId}
          onChange={(e) => setDepartmentId(e.target.value)}
          className="sm:w-56"
        >
          <option value="">All departments</option>
          {(departments || []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
      </div>

      {isLoading ? (
        <LoadingState message="Loading subjects..." />
      ) : isError ? (
        <ErrorState message="Failed to load subjects" onRetry={refetch} />
      ) : subjects.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={BookOpen} title="No subjects found" message="Create your first subject to get started." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Credits</TableHead>
                <TableHead>Weekly periods</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {subjects.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-mono text-xs">{s.code}</TableCell>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell>{s.department_name || '-'}</TableCell>
                  <TableCell>{s.credits}</TableCell>
                  <TableCell>{s.weekly_periods ?? '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setEditing(s)
                          setFormOpen(true)
                        }}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit subject"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(s)}
                        className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        aria-label="Delete subject"
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

      <SubjectForm
        key={editing?.id ?? 'new'}
        open={formOpen}
        subject={editing}
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
        title="Delete subject"
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

function SubjectForm({
  open,
  subject,
  departments,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  subject: Subject | null
  departments: Department[]
  onClose: () => void
  onSubmit: (payload: Partial<Subject>) => void
  submitting: boolean
}) {
  const [name, setName] = useState(subject?.name ?? '')
  const [code, setCode] = useState(subject?.code ?? '')
  const [credits, setCredits] = useState(String(subject?.credits ?? 3))
  const [weeklyPeriods, setWeeklyPeriods] = useState(String(subject?.weekly_periods ?? 4))
  const [departmentId, setDepartmentId] = useState(String(subject?.department_id ?? ''))

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={subject ? 'Edit subject' : 'New subject'}
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
                credits: Number(credits) || 0,
                weekly_periods: Number(weeklyPeriods) || 0,
                department_id: Number(departmentId) || undefined,
              })
            }
            disabled={submitting || !name || !code || !departmentId}
          >
            {subject ? 'Save changes' : 'Create'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Code" required>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. CS101" />
        </Field>
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Data Structures" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Credits" required>
            <Input
              type="number"
              min={0}
              max={10}
              value={credits}
              onChange={(e) => setCredits(e.target.value)}
            />
          </Field>
          <Field label="Weekly periods">
            <Input
              type="number"
              min={0}
              max={20}
              value={weeklyPeriods}
              onChange={(e) => setWeeklyPeriods(e.target.value)}
            />
          </Field>
        </div>
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
    </Modal>
  )
}


