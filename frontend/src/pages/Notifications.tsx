import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Bell, CheckCircle, Trash2 } from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'react-hot-toast'

export default function Notifications() {
  const queryClient = useQueryClient()
  const [showAll, setShowAll] = useState(false)

  const { data: summary } = useQuery({
    queryKey: ['notification-summary'],
    queryFn: () => api.getNotificationSummary(),
  })

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.getNotifications(1, showAll ? 100 : 10),
  })

  const handleMarkAsRead = async (id: number) => {
    try {
      await api.markNotificationAsRead(id)
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
    } catch (error: any) {
      toast.error('Failed to mark as read')
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await api.markAllNotificationsAsRead()
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
      toast.success('All notifications marked as read')
    } catch (error: any) {
      toast.error('Failed to mark all as read')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.deleteNotification(id)
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('Notification deleted')
    } catch (error: any) {
      toast.error('Failed to delete')
    }
  }

  const notificationTypeColors: Record<string, string> = {
    assignment: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    assignment_graded: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    marks_published: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    project: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    default: 'bg-gray-100 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400',
  }

  const notificationIcon = (type: string) => {
    if (type.includes('assignment')) return '📝'
    if (type.includes('marks')) return '🎯'
    if (type.includes('project')) return '💼'
    return '🔔'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Notifications</h1>
          {summary?.unread_count && summary.unread_count > 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {summary.unread_count} unread
            </p>
          )}
        </div>
        {summary?.unread_count && summary.unread_count > 0 && (
          <Button variant="outline" onClick={handleMarkAllAsRead}>
            <CheckCircle className="w-4 h-4 mr-2" />
            Mark all as read
          </Button>
        )}
      </div>

      <div className="space-y-3">
        {(!data?.items || data.items.length === 0) ? (
          <div className="text-center py-12">
            <Bell className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No notifications yet</p>
          </div>
        ) : (
          data.items.map((notification: any) => (
            <div
              key={notification.id}
              className={`rounded-xl p-4 border transition-colors
                ${notification.is_read 
                  ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                  : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'}
              `}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-full ${notificationTypeColors[notification.type] || notificationTypeColors.default}`}>
                    <span>{notificationIcon(notification.type)}</span>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">{notification.title}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{notification.message}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                      {format(new Date(notification.created_at), 'MMM dd, yyyy HH:mm')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!notification.is_read && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleMarkAsRead(notification.id)}
                    >
                      <CheckCircle className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-500 hover:text-red-600"
                    onClick={() => handleDelete(notification.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
