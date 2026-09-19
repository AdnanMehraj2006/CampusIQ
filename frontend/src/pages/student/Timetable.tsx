import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { format } from 'date-fns'
import { Clock, MapPin } from 'lucide-react'

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function StudentTimetable() {
  const { data: timetable, isLoading } = useQuery({
    queryKey: ['my-timetable'],
    queryFn: () => api.getTimetable(),
  })

  const groupedByDay = days.reduce((acc, day) => {
    acc[day] = timetable?.filter((t: any) => t.day === day) || []
    return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Timetable</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {days.map((day) => (
          <div
            key={day}
            className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700"
          >
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">{day}</h3>
            <div className="space-y-2">
              {groupedByDay[day].length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No classes</p>
              ) : (
                groupedByDay[day].map((entry: any) => (
                  <div
                    key={entry.id}
                    className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
                  >
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-1">
                      <Clock className="w-3 h-3" />
                      <span>{format(new Date(`2000-01-01T${entry.start_time}`), 'h:mm a')}</span>
                      <span>-</span>
                      <span>{format(new Date(`2000-01-01T${entry.end_time}`), 'h:mm a')}</span>
                    </div>
                    <p className="font-medium text-gray-900 dark:text-white text-sm">{entry.subject_name}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <MapPin className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-500 dark:text-gray-400">{entry.room_number || 'TBA'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
