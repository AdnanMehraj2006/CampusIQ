import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { AuditLog } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
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
import { Search, ChevronLeft, ChevronRight, ScrollText, Eye } from 'lucide-react'
import { format } from 'date-fns'

const ROLES = ['admin', 'hod', 'faculty', 'cr', 'student']

export default function AdminAuditLogs() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const [role, setRole] = useState('')
  const [selected, setSelected] = useState<AuditLog | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit-logs', page, search, action, resource],
    queryFn: () =>
      api.getAuditLogs({ page, pageSize: 15, q: search || undefined, action: action || undefined, resource: resource || undefined }),
  })

  const { data: actions } = useQuery({
    queryKey: ['audit-actions'],
    queryFn: () => api.getAuditActions(),
  })

  const rows = (data?.items || []) as AuditLog[]
  const filtered = role ? rows.filter((r) => r.role === role) : rows
  const pagination = data?.pagination

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        subtitle="Immutable record of security-sensitive actions across the system"
      />

      <Card>
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Search by user or action..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} className="sm:w-52">
            <option value="">All actions</option>
            {(actions || []).map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </Select>
          <Input
            placeholder="Resource (e.g. user)"
            value={resource}
            onChange={(e) => { setResource(e.target.value); setPage(1) }}
            className="sm:w-44"
          />
          <Select value={role} onChange={(e) => setRole(e.target.value)} className="sm:w-36">
            <option value="">All roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading audit logs..." />
      ) : isError ? (
        <ErrorState message="Failed to load audit logs" onRetry={refetch} />
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={ScrollText}
            title="No audit entries found"
            message="Try adjusting your search or filters."
          />
        </Card>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>IP</TableHead>
                <TableHead className="text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="whitespace-nowrap text-gray-600 dark:text-gray-300">
                    {row.created_at ? format(new Date(row.created_at), 'MMM dd, yyyy · HH:mm') : '-'}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">{row.user_name || `User #${row.user_id}`}</div>
                    {row.user_id && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">ID: {row.user_id}</div>
                    )}
                  </TableCell>
                  <TableCell>
                    {row.role ? (
                      <Badge variant="secondary">{row.role}</Badge>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{row.action}</TableCell>
                  <TableCell>
                    <div className="text-sm">{row.resource}</div>
                    {row.resource_id && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">#{row.resource_id}</div>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-gray-500 dark:text-gray-400">
                    {row.ip_address || '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.details ? (
                      <Button size="sm" variant="ghost" onClick={() => setSelected(row)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
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
            Page {pagination.page} of {pagination.total_pages} · {pagination.total} entries
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

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={`Details: ${selected?.action || ''}`}
        description={selected ? `${selected.resource} #${selected.resource_id || '-'}` : ''}
      >
        {selected && (
          <pre className="max-h-[60vh] overflow-auto rounded-lg bg-gray-50 p-4 text-xs dark:bg-gray-900">
            {JSON.stringify(selected.details, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  )
}
