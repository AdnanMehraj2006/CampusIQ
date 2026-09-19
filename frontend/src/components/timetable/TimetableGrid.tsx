import { TimetableEntry } from '@/types'
import { Card } from '@/components/ui/card'
import { Clock, MapPin, User } from 'lucide-react'
import { format } from 'date-fns'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export function TimetableGrid({ entries }: { entries: TimetableEntry[] }) {
  const groupedByDay = DAYS.reduce<Record<string, TimetableEntry[]>>((acc, day) => {
    acc[day] = entries.filter((t) => t.day === day)
    return acc
  }, {} as Record<string, TimetableEntry[]>)

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {DAYS.map((day) => (
        <Card key={day} className="p-4">
          <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">{day}</h3>
          <div className="space-y-2">
            {groupedByDay[day].length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No classes</p>
            ) : (
              groupedByDay[day]
                .sort((a, b) => a.period - b.period)
                .map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-600 dark:bg-gray-700/50"
                  >
                    <div className="mb-1 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <Clock className="h-3 w-3" />
                      <span>{formatTime(entry.start_time)}</span>
                      <span>-</span>
                      <span>{formatTime(entry.end_time)}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {entry.subject_name || entry.subject_code || `Subject #${entry.subject_id}`}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                      {entry.faculty_name && (
                        <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                          <User className="h-3 w-3" />
                          {entry.faculty_name}
                        </span>
                      )}
                      <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                        <MapPin className="h-3 w-3" />
                        {entry.room_number || 'TBA'}
                      </span>
                      {entry.section && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">Sec {entry.section}</span>
                      )}
                    </div>
                  </div>
                ))
            )}
          </div>
        </Card>
      ))}
    </div>
  )
}

function formatTime(time?: string): string {
  if (!time) return '-'
  try {
    return format(new Date(`2000-01-01T${time}`), 'h:mm a')
  } catch {
    return time
  }
}
