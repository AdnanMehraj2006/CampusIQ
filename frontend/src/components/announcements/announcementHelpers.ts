import { Announcement } from '@/types'

export const PRIORITY_VARIANT: Record<string, 'danger' | 'warning' | 'info' | 'secondary'> = {
  critical: 'danger',
  high: 'warning',
  normal: 'info',
  low: 'secondary',
}

export const TARGET_LABELS: Record<string, string> = {
  everyone: 'Everyone',
  department: 'Department',
  course: 'Course',
  faculty: 'Faculty',
}

export function targetTypeLabel(a: Announcement): string {
  return TARGET_LABELS[a.target_type] || a.target_type
}

export function priorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1)
}
