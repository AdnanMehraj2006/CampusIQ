import { downloadFile } from '@/lib/api'

export async function downloadAttachment(
  assignmentId: number,
  filename: string
): Promise<void> {
  const response = await downloadFile('assignment', assignmentId, filename)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Failed to download file')
  }
  
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
