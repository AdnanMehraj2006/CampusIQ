import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { Project, ProjectMilestone } from '@/types'

export default function FacultyProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
  })
  const { data: milestones } = useQuery({
    queryKey: ['project-milestones', projectId],
    queryFn: () => api.getMilestones(projectId),
    enabled: !!projectId,
  })

  if (isLoading) return <div className="p-8 text-center">Loading...</div>
  if (isError) return <div className="p-8 text-center text-red-600">Failed to load project.</div>

  const project = data as Project

  return (
    <div className="p-6">
      <Link to="/faculty/projects" className="text-blue-600 dark:text-blue-400">← Back to Projects</Link>
      <h1 className="text-2xl font-bold mt-4">{project.title}</h1>
      <p className="mt-2 text-gray-700 dark:text-gray-300">{project.description}</p>
      <div className="mt-4">
        <p>Status: {project.status}</p>
        <p>Supervisor: {project.supervisor_name}</p>
        <p>Deadline: {project.deadline?.toString() || 'N/A'}</p>
        <p>Progress: {project.progress_percentage}%</p>
      </div>
      <h2 className="text-xl font-semibold mt-6">Milestones</h2>
      <ul className="mt-2 space-y-2">
        {(!milestones || milestones.length === 0) && (
          <li className="text-sm text-gray-500 dark:text-gray-400">No milestones defined yet.</li>
        )}
        {milestones?.map((m: ProjectMilestone) => (
          <li key={m.id} className="bg-gray-50 dark:bg-gray-700 p-3 rounded">
            <p className="font-medium">{m.title}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Status: {m.status}</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Deadline: {m.deadline?.toString() || 'N/A'}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
