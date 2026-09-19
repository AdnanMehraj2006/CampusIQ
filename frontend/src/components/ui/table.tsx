import * as React from 'react'
import { cn } from '@/lib/utils'

const TableWrapper = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800',
        className
      )}
      {...props}
    />
  )
)
TableWrapper.displayName = 'TableWrapper'

const Table = React.forwardRef<HTMLTableElement, React.TableHTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} />
  )
)
Table.displayName = 'Table'

const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <thead
      ref={ref}
      className={cn('border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-700/50', className)}
      {...props}
    />
  )
)
TableHeader.displayName = 'TableHeader'

const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn('divide-y divide-gray-200 dark:divide-gray-700', className)} {...props} />
  )
)
TableBody.displayName = 'TableBody'

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn('transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/30', className)}
      {...props}
    />
  )
)
TableRow.displayName = 'TableRow'

const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        'h-11 px-6 text-left align-middle text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400',
        className
      )}
      {...props}
    />
  )
)
TableHead.displayName = 'TableHead'

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn('px-6 py-4 align-middle text-gray-900 dark:text-white', className)} {...props} />
  )
)
TableCell.displayName = 'TableCell'

export { TableWrapper, Table, TableHeader, TableBody, TableRow, TableHead, TableCell }
