import { Announcement } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Pin, Paperclip, Clock, User } from 'lucide-react'
import { format } from 'date-fns'
import { PRIORITY_VARIANT, targetTypeLabel, priorityLabel } from './announcementHelpers'

interface AnnouncementItemProps {
  announcement: Announcement
  onClick?: (a: Announcement) => void
  actions?: React.ReactNode
  compact?: boolean
}

export function AnnouncementItem({ announcement: a, onClick, actions, compact }: AnnouncementItemProps) {
  const isCritical = a.priority === 'critical'
  return (
    <div
      className={`rounded-xl border p-5 transition-shadow ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      } ${
        isCritical
          ? 'border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-950/20'
          : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800'
      }`}
      onClick={onClick ? () => onClick(a) : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {a.is_pinned && (
              <Badge variant="purple" className="gap-1">
                <Pin className="h-3 w-3" /> Pinned
              </Badge>
            )}
            <Badge variant={PRIORITY_VARIANT[a.priority] || 'secondary'}>{priorityLabel(a.priority)}</Badge>
            <Badge variant="outline">{targetTypeLabel(a)}</Badge>
          </div>
          <h3 className="mt-2 font-semibold text-gray-900 dark:text-white">{a.title}</h3>
          {!compact && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-600 dark:text-gray-300">
              {a.summary || a.content}
            </p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
            <span className="inline-flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              {a.author_name || 'Unknown'}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {a.published_at ? format(new Date(a.published_at), 'MMM dd, yyyy · HH:mm') : '-'}
            </span>
            {a.attachment_name && (
              <span className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">
                <Paperclip className="h-3.5 w-3.5" />
                {a.attachment_name}
              </span>
            )}
          </div>
        </div>
        {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
      </div>
    </div>
  )
}
