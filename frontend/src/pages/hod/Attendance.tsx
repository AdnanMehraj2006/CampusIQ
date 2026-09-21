import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
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
import { AlertTriangle, Calendar } from 'lucide-react'
import { AttendanceBadge } from './Students'

type HodDashboard = {
  department?: { id: number; name: string; code?: string | null }
  cards: { label: string; value: string | number; sublabel?: string | null }[]
  students_below_threshold?: { id: number; name: string; percentage: number; section: string }[]
  charts?: {
    attendance_zones?: { name: string; value: number }[]
  }
}

export default function HODAttendance() {
  const [section, setSection] = useState('')

  const { data: dash, isLoading: dashLoading, isError: dashError, refetch } = useQuery<HodDashboard>({
    queryKey: ['dashboard', 'hod'],
    queryFn: async () => (await api.getDashboard('hod')) as unknown as HodDashboard,
  })

  // Section options always come from the complete database list.
  const { data: sectionsData } = useQuery({
    queryKey: ['all-sections'],
    queryFn: () => api.getAllSections(),
  })

  const sections = (sectionsData || []).map((s) => s.name)

  const { data: sectionAnalytics, isLoading: secLoading } = useQuery({
    queryKey: ['hod-section-attendance', section],
    queryFn: () => api.getAttendanceBySection(section),
    enabled: !!section,
  })

  if (dashLoading) return <LoadingState message="Loading attendance analytics..." className="pt-20" />
  if (dashError) return <ErrorState message="Failed to load analytics" onRetry={refetch} className="pt-20" />

  const zones = dash?.charts?.attendance_zones || []
  const below = dash?.students_below_threshold || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance Analytics"
        subtitle={dash?.department?.name ? `Department: ${dash.department.name}` : 'Department attendance overview'}
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {zones.map((z) => (
          <Card key={z.name}>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-500 dark:text-gray-400">{z.name}</p>
              <p
                className={`mt-1 text-2xl font-bold ${
                  z.name.toLowerCase() === 'safe'
                    ? 'text-green-600 dark:text-green-400'
                    : z.name.toLowerCase() === 'warning'
                    ? 'text-yellow-600 dark:text-yellow-400'
                    : z.name.toLowerCase() === 'critical'
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-900 dark:text-white'
                }`}
              >
                {z.value}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">students</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Section attendance drill-down</CardTitle>
          <CardDescription>Pick a section to view its live attendance breakdown</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select value={section} onChange={(e) => setSection(e.target.value)} className="sm:w-56">
            <option value="">Select a section</option>
            {sections.map((s) => (
              <option key={s} value={s}>
                Section {s}
              </option>
            ))}
          </Select>

          {!section ? (
            <EmptyState icon={Calendar} title="No section selected" message="Choose a section to see details." />
          ) : secLoading ? (
            <LoadingState message="Loading section..." />
          ) : (
            <SectionAnalytics data={sectionAnalytics} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Students below attendance threshold
          </CardTitle>
          <CardDescription>Students whose attendance is under the required percentage</CardDescription>
        </CardHeader>
        <CardContent>
          {below.length === 0 ? (
            <EmptyState title="All clear" message="No students are below the attendance threshold." />
          ) : (
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Section</TableHead>
                    <TableHead>Attendance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {below.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      <TableCell>{s.section}</TableCell>
                      <TableCell>
                        <AttendanceBadge percentage={s.percentage} />
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

function SectionAnalytics({ data }: { data: unknown }) {
  const d = data as
    | {
        section?: string
        overall?: number
        conducted?: number
        attended?: number
        students?: { id: number; name: string; percentage: number; zone: string }[]
      }
    | undefined

  if (!d) return <EmptyState title="No data" message="No attendance records for this section." />

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Overall</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">
            {typeof d.overall === 'number' ? `${d.overall.toFixed(1)}%` : '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Conducted</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{d.conducted ?? 0}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Attended</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{d.attended ?? 0}</p>
        </div>
      </div>
      {d.students && d.students.length > 0 && (
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
              {d.students.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell>
                    <AttendanceBadge percentage={s.percentage} />
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.zone === 'safe' ? 'success' : s.zone === 'warning' ? 'warning' : 'danger'}>
                      {s.zone}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableWrapper>
      )}
    </div>
  )
}
