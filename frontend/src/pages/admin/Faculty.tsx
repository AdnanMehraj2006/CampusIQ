import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Faculty, Department } from '@/types'
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
import { Search, ChevronLeft, ChevronRight, Users, Plus, Edit2, ShieldBan, ShieldCheck } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AdminFaculty() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [editing, setEditing] = useState<Faculty | null>(null)
  const [deactivating, setDeactivating] = useState<Faculty | null>(null)
  const [credentials, setCredentials] = useState<CreatedCredentials | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-faculty', page, search, departmentId],
    queryFn: () =>
      api.getFaculty({ page, pageSize: 15, q: search || undefined, departmentId: departmentId ? Number(departmentId) : undefined }),
  })

  const { data: departments } = useQuery({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-faculty'] })
  }

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteFaculty(id),
    onSuccess: () => {
      toast.success('Faculty deleted')
      refresh()
      setDeactivating(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to delete faculty'))
    },
  })

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.createFaculty(payload),
    onSuccess: (created) => {
      toast.success('Faculty created')
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
      toast.error(getApiErrorMessage(error, 'Failed to create faculty'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      api.updateFaculty(id, payload),
    onSuccess: () => {
      toast.success('Faculty updated')
      refresh()
      setEditing(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to update faculty'))
    },
  })

  const faculty = data?.items || []
  const pagination = data?.pagination

  return (
    <div className="space-y-6">
      <PageHeader
        title="Faculty Management"
        subtitle="Create, edit, and manage faculty records"
      />

      <Card>
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Search by name, email or college ID..."
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
          <Button onClick={() => setEditing({} as Faculty)} className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Faculty
          </Button>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading faculty..." />
      ) : isError ? (
        <ErrorState message="Failed to load faculty" onRetry={refetch} />
      ) : faculty.length === 0 ? (
        <Card>
          <EmptyState icon={Users} title="No faculty found" message="Try adjusting your search or filters." />
        </Card>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Faculty</TableHead>
                <TableHead>College ID</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Designation</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {faculty.map((f) => (
                <TableRow key={f.id}>
                  <TableCell>
                    <div className="font-medium">{f.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{f.email}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{f.college_id ?? '-'}</TableCell>
                  <TableCell>{f.department_name ?? '-'}</TableCell>
                  <TableCell>{f.designation}</TableCell>
                  <TableCell>
                    <Badge variant={f.role === 'HOD' ? 'purple' : 'info'}>
                      {f.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {f.status === 'active' ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="danger">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(f)}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit faculty"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      {f.status === 'active' ? (
                        <button
                          onClick={() => setDeactivating(f)}
                          className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                          aria-label="Deactivate faculty"
                        >
                          <ShieldBan className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            api.updateFaculty(f.id, { status: 'active' })
                            toast.success('Faculty reactivated')
                            refresh()
                          }}
                          className="rounded-lg p-1.5 text-green-600 transition-colors hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                          aria-label="Activate faculty"
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
            Page {pagination.page} of {pagination.total_pages} · {pagination.total} faculty
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

      <FacultyModal
        key={editing?.id ?? 'closed'}
        faculty={editing}
        departments={departments || []}
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
        title="Delete faculty"
        message={
          <>
            Are you sure you want to delete <strong>{deactivating?.name}</strong>? This action cannot be
            undone and will also remove their associated user account.
          </>
        }
        confirmLabel="Delete"
        destructive
      />

      <CredentialsModal credentials={credentials} onClose={() => setCredentials(null)} />
    </div>
  )
}

function FacultyModal({
  faculty,
  departments,
  submitting,
  onClose,
  onSubmit,
}: {
  faculty: Faculty | null
  departments: Department[]
  submitting?: boolean
  onClose: () => void
  onSubmit: (payload: Record<string, unknown>) => void
}) {
  const [name, setName] = useState(faculty?.name ?? '')
  const [email, setEmail] = useState(faculty?.email ?? '')
  const [designation, setDesignation] = useState(faculty?.designation ?? 'Assistant Professor')
  const [departmentId, setDepartmentId] = useState(faculty?.department_id?.toString() ?? '')
  const [collegeId, setCollegeId] = useState(faculty?.college_id ?? '')

  const canSubmit = name.trim() && email.trim() && departmentId

  return (
    <Modal
      open={faculty !== null}
      onClose={onClose}
      title={faculty ? 'Edit faculty' : 'Add faculty'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({
              name: name.trim(),
              email: email.trim(),
              designation: designation.trim(),
              department_id: Number(departmentId),
              college_id: collegeId.trim() || undefined,
            })}
            disabled={!canSubmit || submitting}
          >
            {faculty ? 'Save changes' : 'Create faculty'}
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
        <Field label="College ID">
          <Input value={collegeId} onChange={(e) => setCollegeId(e.target.value)} placeholder="Leave blank to auto-generate" />
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
        <Field label="Designation">
          <Select value={designation} onChange={(e) => setDesignation(e.target.value)}>
            <option value="Assistant Professor">Assistant Professor</option>
            <option value="Associate Professor">Associate Professor</option>
            <option value="Professor">Professor</option>
            <option value="Reader">Reader</option>
            <option value="Lecturer">Lecturer</option>
          </Select>
        </Field>
        {!faculty && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            A secure temporary password is generated automatically and shown once after creation.
          </p>
        )}
      </div>
    </Modal>
  )
}
