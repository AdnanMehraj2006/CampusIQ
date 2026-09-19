import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { BookOpen } from 'lucide-react'

type MySubject = {
  id: number
  name: string
  code: string
  credits: number
  weekly_periods?: number
  department_id: number
}

export default function FacultySubjects() {
  const { data, isLoading, isError, refetch } = useQuery<MySubject[]>({
    queryKey: ['my-subjects'],
    queryFn: () => api.getMySubjects(),
  })

  return (
    <div className="space-y-6">
      <PageHeader title="My Subjects" subtitle="Subjects you are currently assigned to teach" />

      {isLoading ? (
        <LoadingState message="Loading subjects..." />
      ) : isError ? (
        <ErrorState message="Failed to load subjects" onRetry={refetch} />
      ) : !data || data.length === 0 ? (
        <Card>
          <EmptyState
            icon={BookOpen}
            title="No subjects assigned"
            message="You have not been assigned to any subjects yet. Contact your department head."
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((s) => (
            <Card key={s.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <CardTitle className="truncate">{s.name}</CardTitle>
                    <p className="mt-1 font-mono text-xs text-gray-500 dark:text-gray-400">{s.code}</p>
                  </div>
                  <Badge variant="info">{s.credits} credits</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {s.weekly_periods ? `${s.weekly_periods} periods / week` : 'Schedule not set'}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
