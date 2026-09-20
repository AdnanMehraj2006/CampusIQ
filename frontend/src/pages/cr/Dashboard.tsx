import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export default function CRDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard', 'cr'],
    queryFn: () => api.getDashboard('cr'),
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (isError || !data) {
    return <div className="text-center py-12 text-red-600">Failed to load dashboard data</div>
  }

  const overview = data.class_overview || {}

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">CR Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {data.cards?.map((card, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{card.value}</p>
            {card.sublabel && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.sublabel}</p>}
          </div>
        ))}
      </div>

      {overview && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Class Overview: Section {overview.section || 'N/A'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Overall Attendance</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{overview.overall?.toFixed?.(0) || '0'}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Classes Attended</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{overview.attended || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Classes Conducted</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{overview.conducted || 0}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
