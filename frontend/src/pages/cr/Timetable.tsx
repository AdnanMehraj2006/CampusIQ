import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TimetableGrid } from '@/components/timetable/TimetableGrid'
import { PageHeader } from '@/components/ui/page-header'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Calendar } from 'lucide-react'

export default function CRTimetable() {
  const { data: timetable, isLoading, isError } = useQuery({
    queryKey: ['cr-timetable'],
    queryFn: () => api.getTimetable(),
  })

  if (isLoading) return <LoadingState message="Loading timetable..." className="pt-20" />

  return (
    <div className="space-y-6">
      <PageHeader title="Class Timetable" subtitle="Your class schedule" />
      {isError ? (
        <ErrorState message="Failed to load timetable" />
      ) : !timetable || timetable.length === 0 ? (
        <EmptyState icon={Calendar} title="No classes scheduled" message="There are no classes in your timetable." />
      ) : (
        <TimetableGrid entries={timetable} />
      )}
    </div>
  )
}
