import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export default function HODDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', 'hod'],
    queryFn: () => api.getDashboard('hod'),
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  const dept = (data as any).department || {}
  const attendance = data?.attendance || {}

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">HOD Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {data?.cards?.map((card, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{card.value}</p>
            {card.sublabel && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.sublabel}</p>}
          </div>
        ))}
      </div>

      {dept && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Department: {dept.name || 'N/A'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Students</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{(data as any).totalStudents || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Faculty</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{(data as any).totalFaculty || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Average Attendance</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{(attendance as any).percentage?.toFixed?.(0) || '0'}%</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
