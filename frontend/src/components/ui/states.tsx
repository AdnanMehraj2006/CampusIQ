import * as React from 'react'
import { cn } from '@/lib/utils'
import { Inbox, AlertCircle, Loader2 } from 'lucide-react'

export function LoadingState({ message = 'Loading...', className }: { message?: string; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
      <p className="text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
  )
}

export function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  message,
  action,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>
  title?: string
  message?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <Icon className="h-12 w-12 text-gray-400 dark:text-gray-500" />
      <div>
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">{title}</h3>
        {message && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({
  message = 'Something went wrong',
  onRetry,
  className,
}: {
  message?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <AlertCircle className="h-12 w-12 text-red-500 dark:text-red-400" />
      <div>
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">Failed to load</h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 inline-flex h-9 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Try again
        </button>
      )}
    </div>
  )
}
