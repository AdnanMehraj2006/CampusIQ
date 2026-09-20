import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export default function AdminDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard', 'admin'],
    queryFn: () => api.getDashboard('admin'),
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (isError || !data) {
    return <div className="text-center py-12 text-red-600">Failed to load dashboard data</div>
  }

  const stats = data.cards || []

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Admin Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((card, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{card.value}</p>
            {card.sublabel && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.sublabel}</p>}
          </div>
        ))}
      </div>
    </div>
  )
}
