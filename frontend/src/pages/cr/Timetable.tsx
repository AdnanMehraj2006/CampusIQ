import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TimetableGrid } from '@/components/timetable/TimetableGrid'
import { PageHeader } from '@/components/ui/page-header'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Calendar } from 'lucide-react'

export default function CRTimetable() {
  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard', 'cr'],
    queryFn: () => api.getDashboard('cr'),
  })

  const section = (dashboard as { section?: string } | undefined)?.section

  const { data: timetable, isLoading, isError, refetch } = useQuery({
    queryKey: ['cr-timetable', section],
    queryFn: () => api.getTimetableBySection(section as string),
    enabled: !!section,
  })

  if (dashLoading || isLoading) return <LoadingState message="Loading timetable..." className="pt-20" />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Class Timetable"
        subtitle={section ? `Weekly schedule for Section ${section}` : 'Your class schedule'}
      />
      {!section ? (
        <EmptyState icon={Calendar} title="No section linked" message="Your profile has no section assigned." />
      ) : isError ? (
        <ErrorState message="Failed to load timetable" onRetry={refetch} />
      ) : !timetable || timetable.length === 0 ? (
        <EmptyState icon={Calendar} title="No classes scheduled" message="The timetable for your section is empty." />
      ) : (
        <TimetableGrid entries={timetable} />
      )}
    </div>
  )
}
