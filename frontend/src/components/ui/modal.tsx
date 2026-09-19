import * as React from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  description?: React.ReactNode
  children: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const sizeStyles = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

export function Modal({ open, onClose, title, description, children, footer, size = 'md', className }: ModalProps) {
  React.useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative w-full rounded-xl bg-white shadow-xl dark:bg-gray-800 max-h-[90vh] flex flex-col',
          sizeStyles[size],
          className
        )}
      >
        {(title || description) && (
          <div className="flex items-start justify-between gap-4 border-b border-gray-200 p-6 dark:border-gray-700">
            <div className="min-w-0">
              {title && (
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
              )}
              {description && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="shrink-0 rounded-lg p-1 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}
        <div className="overflow-y-auto p-6">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-gray-200 p-6 dark:border-gray-700">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
}: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button
            onClick={onClose}
            className="inline-flex h-9 items-center justify-center rounded-lg border border-gray-300 bg-transparent px-4 text-sm font-medium transition-colors hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-800 dark:text-gray-200"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              'inline-flex h-9 items-center justify-center rounded-lg px-4 text-sm font-medium text-white transition-colors',
              destructive ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            )}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <div className="text-sm text-gray-600 dark:text-gray-300">{message}</div>
    </Modal>
  )
}
