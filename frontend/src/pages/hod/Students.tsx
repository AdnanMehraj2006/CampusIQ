import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
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
import { Search, ChevronLeft, ChevronRight, GraduationCap } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function HODStudents() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [section, setSection] = useState('')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-students', page, search, section],
    queryFn: () =>
      api.getStudents({ page, pageSize: 15, q: search || undefined, section: section || undefined }),
  })

  const students = data?.items || []
  const pagination = data?.pagination
  const sections = Array.from(new Set(students.map((s) => s.section).filter(Boolean)))

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
                <TableHead>Attendance</TableHead>
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
                    <AttendanceBadge percentage={s.attendance_percentage} />
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
