import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Subject } from '@/types'
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
import { Plus, MessageSquare, Star } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { format } from 'date-fns'

export default function CRFeedback() {
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['cr-feedback'],
    queryFn: () => api.getFeedback(1, 50),
  })

  const createMutation = useMutation({
    mutationFn: (payload: {
      target_type: string
      subject_id?: number
      rating: number
      message: string
    }) => api.submitFeedback(payload),
    onSuccess: () => {
      toast.success('Feedback submitted')
      queryClient.invalidateQueries({ queryKey: ['cr-feedback'] })
      setFormOpen(false)
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to submit feedback')),
  })

  const feedback = data?.items || []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feedback"
        subtitle="Share anonymous constructive feedback about your classes"
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Feedback
          </Button>
        }
      />

      {isLoading ? (
        <LoadingState message="Loading feedback..." />
      ) : isError ? (
        <ErrorState message="Failed to load feedback" onRetry={refetch} />
      ) : feedback.length === 0 ? (
        <Card>
          <EmptyState
            icon={MessageSquare}
            title="No feedback yet"
            message="Your submitted feedback will appear here."
            action={
              <Button onClick={() => setFormOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New feedback
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {feedback.map((f) => (
            <Card key={f.id}>
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={f.status === 'open' ? 'warning' : 'success'}>{f.status}</Badge>
                  {f.subject_name && <Badge variant="outline">{f.subject_name}</Badge>}
                  <span className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`h-3.5 w-3.5 ${
                          i < f.rating
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-300 dark:text-gray-600'
                        }`}
                      />
                    ))}
                  </span>
                </div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{f.message}</p>
                {f.response && (
                  <div className="mt-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
                    <p className="text-xs font-medium text-gray-900 dark:text-white">Response</p>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{f.response}</p>
                  </div>
                )}
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {f.created_at ? format(new Date(f.created_at), 'MMM dd, yyyy') : ''}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <FeedbackFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
        submitting={createMutation.isPending}
      />
    </div>
  )
}

function FeedbackFormModal({
  open,
  onClose,
  onSubmit,
  submitting,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (payload: { target_type: string; subject_id?: number; rating: number; message: string }) => void
  submitting: boolean
}) {
  const [targetType, setTargetType] = useState('subject')
  const [subjectId, setSubjectId] = useState('')
  const [rating, setRating] = useState(5)
  const [message, setMessage] = useState('')

  const { data: subjects } = useQuery<Subject[]>({
    queryKey: ['cr-subjects'],
    queryFn: () => api.getAllSubjects(),
    enabled: open,
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New feedback"
      description="Feedback is reviewed by the department administration"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                target_type: targetType,
                subject_id: targetType === 'subject' ? Number(subjectId) || undefined : undefined,
                rating,
                message: message.trim(),
              })
            }
            disabled={submitting || (targetType === 'subject' && !subjectId) || message.trim().length < 5}
          >
            Submit feedback
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Target" required>
          <Select value={targetType} onChange={(e) => setTargetType(e.target.value)}>
            <option value="subject">A subject</option>
            <option value="department">The department</option>
          </Select>
        </Field>
        {targetType === 'subject' && (
          <Field label="Subject" required>
            <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">Select a subject</option>
              {(subjects || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} - {s.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label="Rating" required>
          <div className="flex items-center gap-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setRating(i + 1)}
                className="p-1"
                aria-label={`${i + 1} stars`}
              >
                <Star
                  className={`h-6 w-6 ${
                    i < rating
                      ? 'fill-yellow-400 text-yellow-400'
                      : 'text-gray-300 dark:text-gray-600'
                  }`}
                />
              </button>
            ))}
          </div>
        </Field>
        <Field label="Message" required>
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="What went well, what could be better?"
            className="min-h-[120px]"
          />
        </Field>
      </div>
    </Modal>
  )
}

type ApiErrorShape = { data?: { detail?: string } }
