import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TimetableGrid } from '@/components/timetable/TimetableGrid'
import { PageHeader } from '@/components/ui/page-header'
import { Select } from '@/components/ui/select'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Calendar } from 'lucide-react'

export default function HODTimetable() {
  const [section, setSection] = useState('')

  const { data: students } = useQuery({
    queryKey: ['hod-students-sections'],
    queryFn: () => api.getStudents({ pageSize: 100 }),
  })

  const sections = Array.from(new Set((students?.items || []).map((s) => s.section).filter(Boolean)))

  const { data: all, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-timetable'],
    queryFn: () => api.getAllTimetableEntries(1, 500),
  })

  const entries = (all?.items || []).filter((e) => !section || e.section === section)

  return (
    <div className="space-y-6">
      <PageHeader title="Timetable" subtitle="Department weekly schedule" />

      <Select value={section} onChange={(e) => setSection(e.target.value)} className="sm:w-56">
        <option value="">All sections</option>
        {sections.map((s) => (
          <option key={s} value={s}>
            Section {s}
          </option>
        ))}
      </Select>

      {isLoading ? (
        <LoadingState message="Loading timetable..." />
      ) : isError ? (
        <ErrorState message="Failed to load timetable" onRetry={refetch} />
      ) : entries.length === 0 ? (
        <EmptyState icon={Calendar} title="No classes scheduled" message="There are no timetable entries to show." />
      ) : (
        <TimetableGrid entries={entries} />
      )}
    </div>
  )
}
