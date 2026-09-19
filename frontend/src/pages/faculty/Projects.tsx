import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Project } from '@/types'

export default function FacultyProjects() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['supervisedProjects'],
    queryFn: () => api.getSupervisedProjects(),
  })

  if (isLoading) return <div className="p-8 text-center">Loading...</div>
  if (isError) return <div className="p-8 text-center text-red-600">Failed to load projects.</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Supervised Projects</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.items?.map((p: Project) => (
          <div key={p.id} className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow border border-gray-200 dark:border-gray-700">
            <Link to={`/faculty/projects/${p.id}`} className="text-lg font-medium text-blue-600 dark:text-blue-400">
              {p.title}
            </Link>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Status: {p.status}</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">Progress: {p.progress_percentage}%</p>
          </div>
        ))}
      </div>
    </div>
  )
}
