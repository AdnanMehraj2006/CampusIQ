import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { Calendar } from 'lucide-react'

export default function CRAttendance() {
  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard', 'cr'],
    queryFn: () => api.getDashboard('cr'),
  })

  if (dashLoading) return <LoadingState message="Loading attendance..." className="pt-20" />

  const data = dashboard as {
    attendance?: {
      overall?: number
      conducted?: number
      attended?: number
      students?: Array<{
        id: number
        name: string
        percentage: number
        zone: string
      }>
    }
  } | undefined

  const overview = data?.attendance

  return (
    <div className="space-y-6">
      <PageHeader title="Class Attendance" subtitle="Your class attendance overview" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Class average</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
              {typeof overview?.overall === 'number' ? `${overview.overall.toFixed(1)}%` : '-'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Classes conducted</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{overview?.conducted ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Classes attended</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{overview?.attended ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Classmates</CardTitle>
          <CardDescription>Attendance zone per student in your class</CardDescription>
        </CardHeader>
        <CardContent>
          {!overview?.students || overview.students.length === 0 ? (
            <EmptyState title="No records" message="No attendance has been recorded for your class yet." />
          ) : (
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Attendance</TableHead>
                    <TableHead>Zone</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {overview.students.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      <TableCell>{typeof s.percentage === 'number' ? `${s.percentage.toFixed(1)}%` : '-'}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            s.zone === 'safe' ? 'success' : s.zone === 'warning' ? 'warning' : 'danger'
                          }
                        >
                          {s.zone}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableWrapper>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
