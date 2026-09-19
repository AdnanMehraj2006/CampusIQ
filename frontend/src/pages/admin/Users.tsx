import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { UserAdmin, Role } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { Search, ChevronLeft, ChevronRight, Users, ShieldBan, ShieldCheck, Edit2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

const ROLES: Role[] = ['ADMIN', 'HOD', 'FACULTY', 'CR', 'STUDENT']
const STATUSES = ['active', 'suspended']

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')
  const [editing, setEditing] = useState<UserAdmin | null>(null)
  const [suspending, setSuspending] = useState<UserAdmin | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-users', page, search, role, status],
    queryFn: () =>
      api.getUsers({ page, pageSize: 15, q: search || undefined, role: role || undefined, status: status || undefined }),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-users'] })
  }

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<UserAdmin> }) => api.updateUser(id, payload),
    onSuccess: () => {
      toast.success('User updated')
      refresh()
      setEditing(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to update user'))
    },
  })

  const suspendMutation = useMutation({
    mutationFn: (id: number) => api.suspendUser(id),
    onSuccess: () => {
      toast.success('User suspended and sessions revoked')
      refresh()
      setSuspending(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to suspend user'))
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id: number) => api.activateUser(id),
    onSuccess: () => {
      toast.success('User reactivated')
      refresh()
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to activate user'))
    },
  })

  const users = data?.items || []
  const pagination = data?.pagination

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        subtitle="Accounts are created through the Students and Faculty pages"
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
          <Select value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }} className="sm:w-40">
            <option value="">All roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r.toLowerCase()}>
                {r}
              </option>
            ))}
          </Select>
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="sm:w-40">
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading users..." />
      ) : isError ? (
        <ErrorState message="Failed to load users" onRetry={refetch} />
      ) : users.length === 0 ? (
        <Card>
          <EmptyState icon={Users} title="No users found" message="Try adjusting your search or filters." />
        </Card>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>College ID</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last login</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="font-medium">{u.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{u.email}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{u.college_id || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'ADMIN' ? 'danger' : u.role === 'HOD' ? 'purple' : 'info'}>
                      {u.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {u.status === 'active' ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="danger">Suspended</Badge>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                    {u.last_login_at ? format(new Date(u.last_login_at), 'MMM dd, yyyy · HH:mm') : 'Never'}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(u)}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit user"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      {u.status === 'active' ? (
                        <button
                          onClick={() => setSuspending(u)}
                          className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                          aria-label="Suspend user"
                        >
                          <ShieldBan className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => activateMutation.mutate(u.id)}
                          disabled={activateMutation.isPending}
                          className="rounded-lg p-1.5 text-green-600 transition-colors hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                          aria-label="Activate user"
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
            Page {pagination.page} of {pagination.total_pages} · {pagination.total} users
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

      <EditUserModal
        key={editing?.id ?? 'closed'}
        user={editing}
        onClose={() => setEditing(null)}
        onSubmit={(payload) => editing && updateMutation.mutate({ id: editing.id, payload })}
        submitting={updateMutation.isPending}
      />

      <ConfirmDialog
        open={!!suspending}
        onClose={() => setSuspending(null)}
        onConfirm={() => suspending && suspendMutation.mutate(suspending.id)}
        title="Suspend user"
        message={
          <>
            Are you sure you want to suspend <strong>{suspending?.name}</strong> ({suspending?.email})? They will be
            immediately signed out and unable to log in until reactivated.
          </>
        }
        confirmLabel="Suspend"
        destructive
      />
    </div>
  )
}

function EditUserModal({
  user,
  onClose,
  onSubmit,
  submitting,
}: {
  user: UserAdmin | null
  onClose: () => void
  onSubmit: (payload: Partial<UserAdmin>) => void
  submitting: boolean
}) {
  const [name, setName] = useState(user?.name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [role, setRole] = useState((user?.role ?? 'student').toLowerCase())

  return (
    <Modal
      open={!!user}
      onClose={onClose}
      title="Edit user"
      description={user ? `${user.college_id} · ${user.email}` : ''}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({ name, email, phone: phone || undefined, role: role.toUpperCase() as Role })}
            disabled={submitting}
          >
            Save changes
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
        <Field label="Phone">
          <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Optional" />
        </Field>
        <Field label="Role" hint="Changing the role is recorded in the audit log">
          <Select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r} value={r.toLowerCase()}>
                {r}
              </option>
            ))}
          </Select>
        </Field>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Passwords are never exposed. Use the account's own password-reset flow to change credentials.
        </p>
      </div>
    </Modal>
  )
}

type ApiErrorShape = { data?: { detail?: string } }
