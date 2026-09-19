import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Field } from '@/components/ui/page-header'
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
import {
  Download,
  Eye,
  Calendar,
  TrendingUp,
  Users,
  FolderKanban,
  Building2,
  FileSpreadsheet,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

type ReportKey =
  | 'attendance'
  | 'performance'
  | 'faculty-workload'
  | 'project-progress'
  | 'assignment-submissions'
  | 'department'

interface ReportDef {
  key: ReportKey
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  roles: string[]
  needsSection?: boolean
  needsDepartment?: boolean
  needsAssignment?: boolean
}

const REPORTS: ReportDef[] = [
  {
    key: 'attendance',
    title: 'Attendance Report',
    description: 'Per-student attendance totals, percentages and zone for the selected scope.',
    icon: Calendar,
    roles: ['admin', 'hod', 'faculty'],
    needsSection: true,
  },
  {
    key: 'performance',
    title: 'Performance Report',
    description: 'Assessment totals and overall percentage per student in scope.',
    icon: TrendingUp,
    roles: ['admin', 'hod', 'faculty'],
  },
  {
    key: 'faculty-workload',
    title: 'Faculty Workload Report',
    description: 'Assigned subjects and weekly periods per faculty member.',
    icon: Users,
    roles: ['admin', 'hod'],
  },
  {
    key: 'project-progress',
    title: 'Project Progress Report',
    description: 'Groups, milestones completed and progress for projects in scope.',
    icon: FolderKanban,
    roles: ['admin', 'hod', 'faculty'],
  },
  {
    key: 'assignment-submissions',
    title: 'Assignment Submissions',
    description: 'Submission, lateness and grade status per student for one assignment.',
    icon: FileSpreadsheet,
    roles: ['admin', 'hod', 'faculty'],
    needsAssignment: true,
  },
  {
    key: 'department',
    title: 'Department Report',
    description: 'Students, faculty, subjects and average attendance per department.',
    icon: Building2,
    roles: ['admin', 'hod'],
    needsDepartment: true,
  },
]

function parseCsv(text: string): { headers: string[]; rows: string[][] } {
  const lines = text.trim().split(/\r?\n/)
  if (lines.length === 0) return { headers: [], rows: [] }
  const parseLine = (line: string): string[] => {
    const out: string[] = []
    let cur = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i++) {
      const ch = line[i]
      if (inQuotes) {
        if (ch === '"') {
          if (line[i + 1] === '"') {
            cur += '"'
            i++
          } else {
            inQuotes = false
          }
        } else {
          cur += ch
        }
      } else if (ch === '"') {
        inQuotes = true
      } else if (ch === ',') {
        out.push(cur)
        cur = ''
      } else {
        cur += ch
      }
    }
    out.push(cur)
    return out
  }
  return {
    headers: parseLine(lines[0]),
    rows: lines.slice(1).map(parseLine),
  }
}

interface ReportsPageProps {
  /** Lowercase role used to filter which reports are shown. */
  role: 'admin' | 'hod' | 'faculty'
}

export function ReportsPage({ role }: ReportsPageProps) {
  const [format, setFormat] = useState<'csv' | 'pdf'>('csv')
  const [section, setSection] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [assignmentId, setAssignmentId] = useState('')
  const [preview, setPreview] = useState<{ title: string; path: string } | null>(null)

  const { data: departments } = useQuery({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
  })

  const { data: assignmentsData } = useQuery({
    queryKey: ['report-assignments'],
    queryFn: () => api.getAssignments(1, 200),
  })

  const { data: sections } = useQuery<string[]>({
    queryKey: ['report-sections'],
    queryFn: async () => {
      const rows = await api.getStudents({ pageSize: 100 })
      return Array.from(new Set(rows.items.map((s) => s.section).filter(Boolean)))
    },
  })

  const available = REPORTS.filter((r) => r.roles.includes(role))

  const buildPath = (def: ReportDef): string => {
    const params = new URLSearchParams({ format })
    if (def.needsSection && section) params.append('section', section)
    if (def.needsDepartment && departmentId) params.append('department_id', departmentId)
    if (def.needsAssignment && assignmentId) params.append('assignment_id', assignmentId)
    return `/reports/${def.key}?${params.toString()}`
  }

  const handleDownload = async (def: ReportDef) => {
    const run = async () => {
      switch (def.key) {
        case 'attendance':
          await api.getAttendanceReport(format, section || undefined)
          break
        case 'performance':
          await api.getPerformanceReport(format)
          break
        case 'faculty-workload':
          await api.getFacultyWorkloadReport(format)
          break
        case 'project-progress':
          await api.getProjectProgressReport(format)
          break
        case 'assignment-submissions':
          if (!assignmentId) throw new Error('Select an assignment first.')
          await api.getAssignmentSubmissionsReport(Number(assignmentId), format)
          break
        case 'department':
          await api.getDepartmentReport(departmentId ? Number(departmentId) : undefined, format)
          break
      }
    }
    try {
      await run()
      toast.success(`${def.title} downloaded`)
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to generate report'
      toast.error(msg)
    }
  }

  const missingFilter = (def: ReportDef): boolean =>
    (def.needsAssignment && !assignmentId)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Generate and export attendance, performance, workload and project reports"
      />

      <Card>
        <CardHeader>
          <CardTitle>Export format</CardTitle>
          <CardDescription>Choose the output format applied to every report download</CardDescription>
        </CardHeader>
        <CardContent>
          <Field label="Format">
            <Select value={format} onChange={(e) => setFormat(e.target.value as 'csv' | 'pdf')} className="sm:w-48">
              <option value="csv">CSV (spreadsheet)</option>
              <option value="pdf">PDF (printable)</option>
            </Select>
          </Field>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {available.map((def) => {
          const Icon = def.icon
          return (
            <Card key={def.key} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="rounded-lg bg-blue-50 p-2.5 dark:bg-blue-900/20">
                    <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <CardTitle>{def.title}</CardTitle>
                    <CardDescription className="mt-1">{def.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 space-y-3">
                {def.needsSection && (
                  <Field label="Section" hint="Leave empty for all sections in scope">
                    <Select value={section} onChange={(e) => setSection(e.target.value)}>
                      <option value="">All sections</option>
                      {(sections || []).map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
                {def.needsDepartment && role === 'admin' && (
                  <Field label="Department" hint="Leave empty for all departments">
                    <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                      <option value="">All departments</option>
                      {(departments || []).map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
                {def.needsAssignment && (
                  <Field label="Assignment" required>
                    <Select value={assignmentId} onChange={(e) => setAssignmentId(e.target.value)}>
                      <option value="">Select an assignment</option>
                      {(assignmentsData?.items || []).map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.title} {a.subject_name ? `· ${a.subject_name}` : ''}
                        </option>
                      ))}
                    </Select>
                  </Field>
                )}
                <div className="flex items-center gap-2 pt-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPreview({ title: def.title, path: buildPath(def) })}
                    disabled={missingFilter(def)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleDownload(def)}
                    disabled={missingFilter(def)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download {format.toUpperCase()}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {preview && (
        <ReportPreview title={preview.title} path={preview.path} onClose={() => setPreview(null)} />
      )}
    </div>
  )
}

function ReportPreview({ title, path, onClose }: { title: string; path: string; onClose: () => void }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['report-preview', path],
    queryFn: () => api.previewReportCsv(path),
  })

  const parsed = data ? parseCsv(data) : null

  return (
    <Modal open onClose={onClose} title={title} size="xl" description="CSV preview (first 100 rows)">
      {isLoading ? (
        <LoadingState message="Generating preview..." />
      ) : isError ? (
        <ErrorState
          message={(error as { data?: { detail?: string } })?.data?.detail || 'No data available for this scope.'}
        />
      ) : !parsed || parsed.rows.length === 0 ? (
        <EmptyState title="No rows returned" message="The report scope contains no records." />
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                {parsed.headers.map((h, i) => (
                  <TableHead key={i}>{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {parsed.rows.slice(0, 100).map((row, ri) => (
                <TableRow key={ri}>
                  {row.map((cell, ci) => (
                    <TableCell key={ci} className="whitespace-nowrap">
                      {cell}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableWrapper>
      )}
    </Modal>
  )
}
