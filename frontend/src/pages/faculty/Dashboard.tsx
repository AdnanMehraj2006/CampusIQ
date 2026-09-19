import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Calendar, FileText, GraduationCap, BarChart3 } from 'lucide-react'

export default function FacultyDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', 'faculty'],
    queryFn: () => api.getDashboard('faculty'),
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Faculty Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {data?.cards?.map((card, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{card.value}</p>
            {card.sublabel && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.sublabel}</p>}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Today's Schedule</h2>
          <div className="space-y-3">
            {data?.today_classes?.map((classItem: any, i: number) => (
              <div key={i} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{classItem.subject}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{classItem.time} • {classItem.room}</p>
                </div>
              </div>
            ))}
            {(!data?.today_classes || data.today_classes.length === 0) && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No classes scheduled today</p>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Upcoming Assignments</h2>
          <div className="space-y-3">
            {data?.upcoming_assignments?.map((assignment: any) => (
              <div key={assignment.id} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="font-medium text-gray-900 dark:text-white text-sm">{assignment.title}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Due: {assignment.deadline}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
