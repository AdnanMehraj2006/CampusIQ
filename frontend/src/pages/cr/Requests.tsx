import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { CRRequest } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
import { Field } from '@/components/ui/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/states'
import { Plus, FileText } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

const REQUEST_TYPES = [
  { value: 'general', label: 'General request' },
  { value: 'maintenance', label: 'Maintenance / facilities' },
  { value: 'academic', label: 'Academic / rescheduling' },
  { value: 'event', label: 'Event / permission' },
  { value: 'other', label: 'Other' },
]

export default function CRRequests() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [selected, setSelected] = useState<CRRequest | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['cr-requests'],
    queryFn: () => api.getCRRequests({ pageSize: 50 }),
  })

  const createMutation = useMutation({
    mutationFn: (payload: { request_type: string; title: string; description: string }) =>
      api.createCRRequest(payload),
    onSuccess: () => {
      toast.success('Request submitted')
      queryClient.invalidateQueries({ queryKey: ['cr-requests'] })
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to submit request')),
  })

  const requests = data?.items || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Class Requests"
        subtitle="Raise and track requests on behalf of your class"
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Request
          </Button>
        }
      />

      {isLoading ? (
        <LoadingState message="Loading requests..." />
      ) : isError ? (
        <ErrorState message="Failed to load requests" onRetry={refetch} />
      ) : requests.length === 0 ? (
        <Card>
          <EmptyState
            icon={FileText}
            title="No requests yet"
            message="Raise a request to the administration on behalf of your class."
            action={
              <Button onClick={() => setFormOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New request
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {requests.map((r) => (
            <Card
              key={r.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => setSelected(r)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={r.status === 'open' ? 'warning' : 'success'}>{r.status}</Badge>
                      <Badge variant="outline">
                        {REQUEST_TYPES.find((t) => t.value === r.request_type)?.label || r.request_type}
                      </Badge>
                    </div>
                    <h3 className="mt-2 font-semibold text-gray-900 dark:text-white">{r.title}</h3>
                    <p className="mt-1 line-clamp-2 text-sm text-gray-600 dark:text-gray-300">{r.description}</p>
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {r.created_at ? format(new Date(r.created_at), 'MMM dd, yyyy') : ''}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <RequestFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
        submitting={createMutation.isPending}
      />

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.title}
        description={selected ? `Submitted ${selected.created_at ? format(new Date(selected.created_at), 'MMM dd, yyyy') : ''}` : ''}
      >
        {selected && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={selected.status === 'open' ? 'warning' : 'success'}>{selected.status}</Badge>
              <Badge variant="outline">
                {REQUEST_TYPES.find((t) => t.value === selected.request_type)?.label || selected.request_type}
              </Badge>
            </div>
            <p className="whitespace-pre-wrap text-sm text-gray-600 dark:text-gray-300">{selected.description}</p>
            {selected.resolution_note && (
              <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-700/50">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">Resolution</h4>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{selected.resolution_note}</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

function RequestFormModal({
  open,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (payload: { request_type: string; title: string; description: string }) => void
  submitting: boolean
}) {
  const [requestType, setRequestType] = useState('general')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New class request"
      description="Your section and department are attached automatically"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit({ request_type: requestType, title: title.trim(), description: description.trim() })}
            disabled={submitting || title.trim().length < 3 || description.trim().length < 5}
          >
            Submit request
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Type" required>
          <Select value={requestType} onChange={(e) => setRequestType(e.target.value)}>
            {REQUEST_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Title" required>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Short summary" maxLength={200} />
        </Field>
        <Field label="Description" required>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the request in detail"
            className="min-h-[120px]"
          />
        </Field>
      </div>
    </Modal>
  )
}

type ApiErrorShape = { data?: { detail?: string } }
