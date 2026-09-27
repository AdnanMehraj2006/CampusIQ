import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TimetableGrid } from '@/components/timetable/TimetableGrid'
import { PageHeader } from '@/components/ui/page-header'
import { Select } from '@/components/ui/select'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Calendar } from 'lucide-react'

export default function HODTimetable() {
  const { data: all, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-timetable'],
    queryFn: () => api.getAllTimetableEntries(1, 500),
  })

  const entries = all?.items || []

  return (
    <div className="space-y-6">
      <PageHeader title="Timetable" subtitle="Department weekly schedule" />

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
