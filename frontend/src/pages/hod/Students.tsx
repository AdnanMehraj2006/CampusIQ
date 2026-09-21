import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
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
import { Search, ChevronLeft, ChevronRight, GraduationCap, UserCheck, UserX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/modal'
import { toast } from 'react-hot-toast'

export default function HODStudents() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [section, setSection] = useState('')
  const [crRemoving, setCrRemoving] = useState<number | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-students', page, search, section],
    queryFn: () =>
      api.getStudents({ page, pageSize: 15, q: search || undefined, section: section || undefined }),
  })

  // Section options always come from the complete database list - never from
  // the currently displayed rows, so filtering can never shrink the options.
  const { data: sectionsData } = useQuery({
    queryKey: ['all-sections'],
    queryFn: () => api.getAllSections(),
  })

  const assignCRMutation = useMutation({
    mutationFn: (id: number) => api.assignCR(id),
    onSuccess: () => toast.success('Student appointed as CR'),
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to assign CR')),
  })

  const removeCRMutation = useMutation({
    mutationFn: (id: number) => api.removeCR(id),
    onSuccess: () => {
      toast.success('CR status removed')
      setCrRemoving(null)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to remove CR')),
  })

  const students = data?.items || []
  const pagination = data?.pagination
  const sections = sectionsData?.map((s) => s.name) || []

  return (
    <div className="space-y-6">
      <PageHeader title="Students" subtitle="Student records within your access scope" />

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
          <Select value={section} onChange={(e) => { setSection(e.target.value); setPage(1) }} className="sm:w-40">
            <option value="">All sections</option>
            {sections.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading students..." />
      ) : isError ? (
        <ErrorState message="Failed to load students" onRetry={refetch} />
      ) : students.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={GraduationCap} title="No students found" message="Try adjusting your search or filters." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Student</TableHead>
                <TableHead>Enrollment</TableHead>
                <TableHead>Section</TableHead>
                <TableHead>Semester</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Attendance</TableHead>
                <TableHead className="text-right">CR</TableHead>
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
                  <TableCell>{s.section}</TableCell>
                  <TableCell>{s.semester_number ?? '-'}</TableCell>
                  <TableCell>
                    <Badge variant={s.role === 'CR' ? 'warning' : 'info'}>{s.role}</Badge>
                  </TableCell>
                  <TableCell>
                    <AttendanceBadge percentage={s.attendance_percentage} />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      {s.role === 'CR' ? (
                        <button
                          onClick={() => setCrRemoving(s.id)}
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
                          title="Appoint as Class Representative (own department only)"
                        >
                          <UserCheck className="h-4 w-4" />
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

      <ConfirmDialog
        open={crRemoving !== null}
        onClose={() => setCrRemoving(null)}
        onConfirm={() => crRemoving !== null && removeCRMutation.mutate(crRemoving)}
        title="Remove CR status"
        message="The account keeps working as a normal student."
        confirmLabel="Remove CR"
        destructive
      />
    </div>
  )
}

export function AttendanceBadge({ percentage }: { percentage: number | null | undefined }) {
  if (percentage === null || percentage === undefined) {
    return <span className="text-gray-400">-</span>
  }
  const variant = percentage >= 75 ? 'success' : percentage >= 60 ? 'warning' : 'danger'
  return <Badge variant={variant}>{percentage.toFixed(1)}%</Badge>
}
