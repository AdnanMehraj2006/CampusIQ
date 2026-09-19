import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Project } from '@/types'

export default function StudentProjects() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['myProjects'],
    queryFn: () => api.getMyProjects(),
  })

  const joinMutation = useMutation({
    mutationFn: (projectId: number) => api.joinProjectGroup(projectId, 'Group', undefined, []),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['myProjects'] }),
  })

  if (isLoading) return <div className="p-8 text-center">Loading...</div>
  if (isError) return <div className="p-8 text-center text-red-600">Failed to load projects.</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">My Projects</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.items?.map((p: Project) => (
          <div key={p.id} className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow border border-gray-200 dark:border-gray-700">
            <Link to={`/student/projects/${p.id}`} className="text-lg font-medium text-blue-600 dark:text-blue-400">
              {p.title}
            </Link>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Status: {p.status}</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">Progress: {p.progress_percentage}%</p>
            {p.my_group_id ? (
              <span className="mt-2 inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded">Member</span>
            ) : (
              <button
                onClick={() => joinMutation.mutate(p.id)}
                disabled={joinMutation.isPending}
                className="mt-2 px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {joinMutation.isPending ? 'Joining…' : 'Join Group'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
