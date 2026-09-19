import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Department } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { Plus, Edit2, Trash2, Building2, Search } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AdminDepartments() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<Department | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleting, setDeleting] = useState<Department | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-departments'],
    queryFn: () => api.getDepartments({ pageSize: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: (payload: Partial<Department>) => api.createDepartment(payload),
    onSuccess: () => {
      toast.success('Department created')
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] })
      queryClient.invalidateQueries({ queryKey: ['all-departments'] })
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to create department')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Department> }) =>
      api.updateDepartment(id, payload),
    onSuccess: () => {
      toast.success('Department updated')
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] })
      queryClient.invalidateQueries({ queryKey: ['all-departments'] })
      setFormOpen(false)
      setEditing(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to update department')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteDepartment(id),
    onSuccess: () => {
      toast.success('Department deleted')
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] })
      queryClient.invalidateQueries({ queryKey: ['all-departments'] })
      setDeleting(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to delete department')),
  })

  const departments = (data?.items || []).filter((d) =>
    `${d.name} ${d.code}`.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Departments"
        subtitle="Manage academic departments and their heads"
        actions={
          <Button
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Department
          </Button>
        }
      />

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <Input
          placeholder="Search departments..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <LoadingState message="Loading departments..." />
      ) : isError ? (
        <ErrorState message="Failed to load departments" onRetry={refetch} />
      ) : departments.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={Building2} title="No departments found" message="Create your first department to get started." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Head of Department</TableHead>
                <TableHead>Students</TableHead>
                <TableHead>Faculty</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {departments.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">{d.name}</TableCell>
                  <TableCell className="font-mono text-xs">{d.code}</TableCell>
                  <TableCell>{d.hod_name || <span className="text-gray-400">Unassigned</span>}</TableCell>
                  <TableCell>{d.student_count ?? 0}</TableCell>
                  <TableCell>{d.faculty_count ?? 0}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setEditing(d)
                          setFormOpen(true)
                        }}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit department"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleting(d)}
                        className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        aria-label="Delete department"
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

      <DepartmentForm
        key={editing?.id ?? 'new'}
        open={formOpen}
        department={editing}
        onClose={() => {
          setFormOpen(false)
          setEditing(null)
        }}
        onSubmit={(payload) =>
          editing
            ? updateMutation.mutate({ id: editing.id, payload })
            : createMutation.mutate(payload)
        }
        submitting={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Delete department"
        message={
          <>
            Are you sure you want to delete <strong>{deleting?.name}</strong>? Departments with enrolled students
            cannot be deleted.
          </>
        }
        confirmLabel="Delete"
        destructive
      />
    </div>
  )
}

function DepartmentForm({
  open,
  department,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  department: Department | null
  onClose: () => void
  onSubmit: (payload: Partial<Department>) => void
  submitting: boolean
}) {
  const [name, setName] = useState(department?.name ?? '')
  const [code, setCode] = useState(department?.code ?? '')
  const [description, setDescription] = useState(department?.description ?? '')

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={department ? 'Edit department' : 'New department'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={() => onSubmit({ name, code, description })} disabled={submitting || !name || !code}>
            {department ? 'Save changes' : 'Create'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Name" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Computer Science" />
        </Field>
        <Field label="Code" required>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. CSE" maxLength={20} />
        </Field>
        <Field label="Description">
          <Input value={description || ''} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" />
        </Field>
      </div>
    </Modal>
  )
}

type ApiErrorShape = { data?: { detail?: string } }
