import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states'
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { TrendingUp, AlertCircle } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

type HodDashboard = {
  department?: { id: number; name: string }
  subject_performance?: { subject_id: number; subject: string; code: string; average: number; count: number }[]
  students_needing_attention?: { id: number; name: string; percentage: number }[]
  faculty_workload?: { id: number; name: string; designation: string; subjects: number; periods: number }[]
}

export default function HODPerformance() {
  const { data, isLoading, isError, refetch } = useQuery<HodDashboard>({
    queryKey: ['dashboard', 'hod'],
    queryFn: async () => (await api.getDashboard('hod')) as unknown as HodDashboard,
  })

  if (isLoading) return <LoadingState message="Loading performance analytics..." className="pt-20" />
  if (isError) return <ErrorState message="Failed to load analytics" onRetry={refetch} className="pt-20" />

  const subjectPerf = (data?.subject_performance || []).slice(-10)
  const attention = data?.students_needing_attention || []
  const workload = data?.faculty_workload || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Performance Analytics"
        subtitle={data?.department?.name ? `Department: ${data.department.name}` : 'Department performance overview'}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Subject averages
          </CardTitle>
          <CardDescription>Average marks percentage per subject (lowest 10 shown)</CardDescription>
        </CardHeader>
        <CardContent>
          {subjectPerf.length === 0 ? (
            <EmptyState title="No marks data" message="No assessment marks have been recorded yet." />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subjectPerf} margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />
                  <XAxis
                    dataKey="code"
                    tick={{ fontSize: 11, fill: '#9ca3af' }}
                    angle={-35}
                    textAnchor="end"
                    height={56}
                  />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#9ca3af' }} />
                  <Tooltip
                    formatter={(value: number) => [`${value}%`, 'Average']}
                    labelFormatter={(label) => label}
                  />
                  <Bar dataKey="average" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Students needing attention
          </CardTitle>
          <CardDescription>Students averaging below 50% across recorded assessments</CardDescription>
        </CardHeader>
        <CardContent>
          {attention.length === 0 ? (
            <EmptyState title="None" message="No students are currently below the 50% performance threshold." />
          ) : (
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Average</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attention.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      <TableCell className="font-semibold text-red-600 dark:text-red-400">
                        {s.percentage}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableWrapper>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Faculty workload</CardTitle>
          <CardDescription>Assigned subjects and weekly periods per faculty member</CardDescription>
        </CardHeader>
        <CardContent>
          {workload.length === 0 ? (
            <EmptyState title="No faculty" message="No faculty workload data available." />
          ) : (
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Designation</TableHead>
                    <TableHead>Subjects</TableHead>
                    <TableHead>Periods / week</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workload.map((w) => (
                    <TableRow key={w.id}>
                      <TableCell className="font-medium">{w.name}</TableCell>
                      <TableCell>{w.designation || '-'}</TableCell>
                      <TableCell>{w.subjects}</TableCell>
                      <TableCell>{w.periods}</TableCell>
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
