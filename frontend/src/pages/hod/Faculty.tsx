import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
import { Search, Users } from 'lucide-react'

export default function HODFaculty() {
  const [search, setSearch] = useState('')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hod-faculty', search],
    queryFn: () => api.getFaculty({ pageSize: 100, q: search || undefined }),
  })

  const faculty = data?.items || []

  return (
    <div className="space-y-6">
      <PageHeader title="Faculty" subtitle="Faculty members within your access scope" />

      <Card>
        <CardContent className="pt-6">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Search faculty..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState message="Loading faculty..." />
      ) : isError ? (
        <ErrorState message="Failed to load faculty" onRetry={refetch} />
      ) : faculty.length === 0 ? (
        <TableWrapper>
          <EmptyState icon={Users} title="No faculty found" message="Try adjusting your search." />
        </TableWrapper>
      ) : (
        <TableWrapper>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Designation</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Subjects</TableHead>
                <TableHead>Role</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {faculty.map((f) => (
                <TableRow key={f.id}>
                  <TableCell>
                    <div className="font-medium">{f.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{f.email}</div>
                  </TableCell>
                  <TableCell>{f.designation || '-'}</TableCell>
                  <TableCell>{f.department_name || '-'}</TableCell>
                  <TableCell>{f.subject_count ?? 0}</TableCell>
                  <TableCell>
                    {f.is_hod ? (
                      <Badge variant="purple">HOD</Badge>
                    ) : (
                      <Badge variant="info">Faculty</Badge>
                    )}
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
