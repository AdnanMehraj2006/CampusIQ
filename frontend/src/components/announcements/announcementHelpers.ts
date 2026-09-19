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
  semester: 'Semester',
  section: 'Section',
  faculty: 'Faculty',
}

export function targetTypeLabel(a: Announcement): string {
  const base = TARGET_LABELS[a.target_type] || a.target_type
  if (a.target_type === 'section') return `Section ${a.section || '-'}`
  return base
}

export function priorityLabel(priority: string): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1)
}
