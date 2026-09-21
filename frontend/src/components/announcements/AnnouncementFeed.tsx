import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage, downloadFile } from '@/lib/api'
import { Announcement } from '@/types'
import { AnnouncementItem } from './AnnouncementItem'
import { priorityLabel, PRIORITY_VARIANT, targetTypeLabel } from './announcementHelpers'
import { AnnouncementFormModal } from './AnnouncementFormModal'
import { Modal } from '@/components/ui/modal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { ConfirmDialog } from '@/components/ui/modal'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Plus, Search, Pin, Edit2, Trash2, ChevronLeft, ChevronRight, Megaphone } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

const PRIORITIES = ['low', 'normal', 'high', 'critical']

interface AnnouncementFeedProps {
  /** Role-prefixed query key used for cache invalidation, e.g. 'admin-announcements'. */
  queryKey: string
  /** Show create / edit / delete controls (requires PUBLISH_ANNOUNCEMENTS server-side). */
  canManage?: boolean
  title?: string
  subtitle?: string
}

export function AnnouncementFeed({
  queryKey,
  canManage = false,
  title = 'Announcements',
  subtitle,
}: AnnouncementFeedProps) {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [priority, setPriority] = useState('')
  const [pinnedOnly, setPinnedOnly] = useState(false)
  const [selected, setSelected] = useState<Announcement | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Announcement | null>(null)
  const [deleting, setDeleting] = useState<Announcement | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [queryKey, page, search, priority, pinnedOnly],
    queryFn: () =>
      api.getAnnouncements({ page, pageSize: 10, q: search || undefined, priority: priority || undefined, pinnedOnly }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteAnnouncement(id),
    onSuccess: () => {
      toast.success('Announcement deleted')
      queryClient.invalidateQueries({ queryKey: [queryKey] })
      setDeleting(null)
      setSelected(null)
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to delete announcement'))
    },
  })

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleEdit = (a: Announcement) => {
    setEditing(a)
    setSelected(null)
    setFormOpen(true)
  }

  const pagination = data?.pagination
  const items = data?.items || []

  const downloadAttachment = async (announcement: Announcement) => {
    if (announcement.attachment_path) {
      const filename = announcement.attachment_name || 'attachment'
      const response = await downloadFile('announcement', announcement.id, filename)
      if (!response.ok) {
        toast.error('Failed to download file')
        return
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
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
        </div>
        {canManage && (
          <Button
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Announcement
          </Button>
        )}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Search announcements..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1) }} className="sm:w-40">
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {priorityLabel(p)}
            </option>
          ))}
        </Select>
        <Button
          variant={pinnedOnly ? 'default' : 'outline'}
          onClick={() => {
            setPinnedOnly(!pinnedOnly)
            setPage(1)
          }}
          className="shrink-0"
        >
          <Pin className="mr-2 h-4 w-4" />
          Pinned
        </Button>
      </div>

      {isLoading ? (
        <LoadingState message="Loading announcements..." />
      ) : isError ? (
        <ErrorState message="Failed to load announcements" onRetry={refetch} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Megaphone}
          title="No announcements found"
          message={
            search || priority || pinnedOnly
              ? 'Try adjusting your search or filters.'
              : canManage
              ? 'Publish your first announcement to reach your audience.'
              : 'New announcements will appear here.'
          }
          action={
            canManage && !search && !priority && !pinnedOnly ? (
              <Button onClick={() => setFormOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create announcement
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="space-y-3">
            {items.map((a) => (
              <AnnouncementItem
                key={a.id}
                announcement={a}
                onClick={setSelected}
                actions={
                  canManage ? (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEdit(a) }}
                        className="rounded-lg p-1.5 text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        aria-label="Edit announcement"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleting(a) }}
                        className="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                        aria-label="Delete announcement"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </>
                  ) : undefined
                }
              />
            ))}
          </div>

          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-200 pt-4 dark:border-gray-700">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Page {pagination.page} of {pagination.total_pages} · {pagination.total} total
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={pagination.page <= 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
                  disabled={pagination.page >= pagination.total_pages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Detail modal */}
      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.title}
        size="lg"
        footer={
          canManage && selected ? (
            <>
              <Button variant="outline" onClick={() => handleEdit(selected)}>
                <Edit2 className="mr-2 h-4 w-4" />
                Edit
              </Button>
              <Button variant="destructive" onClick={() => setDeleting(selected)}>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </>
          ) : undefined
        }
      >
        {selected && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <AnnouncementBadgeRow announcement={selected} />
            </div>
            {selected.summary && (
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{selected.summary}</p>
            )}
            <div className="whitespace-pre-wrap text-sm text-gray-600 dark:text-gray-300">
              {selected.content}
            </div>
            {selected.attachment_name && (
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); downloadAttachment(selected) }}
                className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                📎 {selected.attachment_name}
              </a>
            )}
            <div className="border-t border-gray-200 pt-4 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
              <p>
                Published by {selected.author_name || 'Unknown'}
                {selected.author_role ? ` · ${selected.author_role}` : ''}
              </p>
              <p>
                {selected.published_at
                  ? format(new Date(selected.published_at), 'MMM dd, yyyy · HH:mm')
                  : ''}
                {selected.expiry_at
                  ? ` · expires ${format(new Date(selected.expiry_at), 'MMM dd, yyyy · HH:mm')}`
                  : ''}
              </p>
            </div>
          </div>
        )}
      </Modal>

      {canManage && (
        <AnnouncementFormModal
          open={formOpen}
          onClose={() => setFormOpen(false)}
          announcement={editing}
          queryKey={queryKey}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
        title="Delete announcement"
        message={`Are you sure you want to delete "${deleting?.title}"? This action cannot be undone.`}
        confirmLabel="Delete"
        destructive
      />
    </div>
  )
}

function AnnouncementBadgeRow({ announcement: a }: { announcement: Announcement }) {
  return (
    <>
      {a.is_pinned && <Badge variant="purple">Pinned</Badge>}
      <Badge variant={PRIORITY_VARIANT[a.priority] || 'secondary'}>{priorityLabel(a.priority)}</Badge>
      <Badge variant="outline">{targetTypeLabel(a)}</Badge>
    </>
  )
}