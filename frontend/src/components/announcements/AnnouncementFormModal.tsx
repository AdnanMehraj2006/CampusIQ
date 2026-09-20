import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { Announcement, Department, Course, Semester } from '@/types'
import { Modal } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Field } from '@/components/ui/page-header'
import { toast } from 'react-hot-toast'
import { Loader2, Paperclip } from 'lucide-react'

const TARGET_OPTIONS: { value: string; label: string }[] = [
  { value: 'everyone', label: 'Everyone' },
  { value: 'department', label: 'Department' },
  { value: 'course', label: 'Course' },
  { value: 'semester', label: 'Semester' },
  { value: 'section', label: 'Section' },
  { value: 'faculty', label: 'Faculty' },
]

const PRIORITIES = ['low', 'normal', 'high', 'critical']

interface AnnouncementFormModalProps {
  open: boolean
  onClose: () => void
  announcement?: Announcement | null
  queryKey: string
}

export function AnnouncementFormModal({ open, onClose, announcement, queryKey }: AnnouncementFormModalProps) {
  const queryClient = useQueryClient()
  const isEditing = !!announcement

  const { data: allowed } = useQuery({
    queryKey: ['announcement-targets'],
    queryFn: () => api.getAnnouncementTargets(),
    enabled: open,
  })

  const { data: departments } = useQuery<Department[]>({
    queryKey: ['all-departments'],
    queryFn: () => api.getAllDepartments(),
    enabled: open,
  })

  const [form, setForm] = useState({
    title: '',
    content: '',
    summary: '',
    target_type: 'everyone',
    department_id: '',
    course_id: '',
    semester_id: '',
    section: '',
    priority: 'normal',
    is_pinned: false,
    expiry_at: '',
  })
  const [attachment, setAttachment] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    if (announcement) {
      setForm({
        title: announcement.title || '',
        content: announcement.content || '',
        summary: announcement.summary || '',
        target_type: announcement.target_type || 'everyone',
        department_id: announcement.department_id ? String(announcement.department_id) : '',
        course_id: announcement.course_id ? String(announcement.course_id) : '',
        semester_id: announcement.semester_id ? String(announcement.semester_id) : '',
        section: announcement.section || '',
        priority: announcement.priority || 'normal',
        is_pinned: !!announcement.is_pinned,
        expiry_at: announcement.expiry_at ? announcement.expiry_at.slice(0, 16) : '',
      })
    } else {
      setForm({
        title: '',
        content: '',
        summary: '',
        target_type: (allowed?.targets?.[0] as string) || 'everyone',
        department_id: '',
        course_id: '',
        semester_id: '',
        section: '',
        priority: 'normal',
        is_pinned: false,
        expiry_at: '',
      })
    }
    setAttachment(null)
  }, [open, announcement, allowed])

  const { data: courses } = useQuery<PaginatedCourses>({
    queryKey: ['form-courses', form.department_id],
    queryFn: () => api.getCourses({ departmentId: Number(form.department_id) || undefined, pageSize: 100 }),
    enabled: open && !!form.department_id,
  })

  const { data: semesters } = useQuery<Semester[]>({
    queryKey: ['form-semesters', form.course_id],
    queryFn: () => api.getSemesters(Number(form.course_id) || undefined),
    enabled: open && !!form.course_id,
  })

  const mutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        title: form.title.trim(),
        content: form.content.trim(),
        summary: form.summary.trim() || undefined,
        target_type: form.target_type,
        priority: form.priority,
        is_pinned: form.is_pinned,
        expiry_at: form.expiry_at ? new Date(form.expiry_at).toISOString() : undefined,
      }
      if (['department', 'course', 'semester', 'section', 'faculty'].includes(form.target_type)) {
        payload.department_id = Number(form.department_id) || undefined
      }
      if (['course', 'semester'].includes(form.target_type)) {
        payload.course_id = Number(form.course_id) || undefined
      }
      if (form.target_type === 'semester') {
        payload.semester_id = Number(form.semester_id) || undefined
      }
      if (form.target_type === 'section') {
        payload.section = form.section.trim() || undefined
      }

      let result: Announcement
      if (isEditing && announcement) {
        result = await api.updateAnnouncement(announcement.id, payload)
      } else {
        result = await api.createAnnouncement(payload)
      }
      if (attachment && result.id) {
        await api.uploadAnnouncementAttachment(result.id, attachment)
      }
      return result
    },
    onSuccess: () => {
      toast.success(isEditing ? 'Announcement updated' : 'Announcement published')
      queryClient.invalidateQueries({ queryKey: [queryKey] })
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
      onClose()
    },
    onError: (error: unknown) => {
      toast.error(getApiErrorMessage(error, 'Failed to save announcement'))
    },
  })

  const allowedTargets: string[] = allowed?.targets || ['everyone']
  const facultySections: string[] = allowed?.sections || []
  const needsDepartment = ['department', 'course', 'semester', 'section', 'faculty'].includes(form.target_type)
  const needsCourse = ['course', 'semester'].includes(form.target_type)
  const needsSemester = form.target_type === 'semester'
  const needsSection = form.target_type === 'section'

  const canSubmit =
    form.title.trim().length >= 3 &&
    form.content.trim().length > 0 &&
    (!needsDepartment || !!form.department_id) &&
    (!needsCourse || !!form.course_id) &&
    (!needsSemester || !!form.semester_id) &&
    (!needsSection || !!form.section)

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={isEditing ? 'Edit Announcement' : 'New Announcement'}
      description={isEditing ? 'Update the announcement content and audience.' : 'Publish a new announcement to the selected audience.'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!canSubmit || mutation.isPending}>
            {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEditing ? 'Save changes' : 'Publish'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Title" required>
          <Input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Announcement title"
            maxLength={200}
          />
        </Field>

        <Field label="Summary" hint="Optional short preview shown in the feed (max 300 characters)">
          <Input
            value={form.summary}
            onChange={(e) => setForm({ ...form, summary: e.target.value })}
            placeholder="One-line summary"
            maxLength={300}
          />
        </Field>

        <Field label="Content" required>
          <Textarea
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            placeholder="Full announcement content"
            className="min-h-[140px]"
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Target audience" required>
            <Select
              value={form.target_type}
              onChange={(e) => setForm({ ...form, target_type: e.target.value, section: '' })}
            >
              {TARGET_OPTIONS.filter((t) => allowedTargets.includes(t.value)).map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Priority">
            <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </option>
              ))}
            </Select>
          </Field>

          {needsDepartment && (
            <Field label="Department" required>
              <Select
                value={form.department_id}
                onChange={(e) => setForm({ ...form, department_id: e.target.value, course_id: '', semester_id: '' })}
              >
                <option value="">Select department</option>
                {(departments || []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {needsCourse && (
            <Field label="Course" required>
              <Select
                value={form.course_id}
                onChange={(e) => setForm({ ...form, course_id: e.target.value, semester_id: '' })}
                disabled={!form.department_id}
              >
                <option value="">Select course</option>
                {(courses?.items || []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {needsSemester && (
            <Field label="Semester" required>
              <Select
                value={form.semester_id}
                onChange={(e) => setForm({ ...form, semester_id: e.target.value })}
                disabled={!form.course_id}
              >
                <option value="">Select semester</option>
                {(semesters || []).map((s) => (
                  <option key={s.id} value={s.id}>
                    Semester {s.semester_number}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          {needsSection && (
            <Field label="Section" required hint={facultySections.length ? 'Limited to sections you teach' : 'No sections available for your subjects'}>
              {facultySections.length ? (
                <Select value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })}>
                  <option value="">Select section</option>
                  {facultySections.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              ) : (
                <div className="text-sm text-gray-500 dark:text-gray-400">No sections available</div>
              )}
            </Field>
          )}

           <Field label="Expiry" hint="Optional - select a date AND time (DD-MM-YYYY, HH:MM)">
             <Input
               type="datetime-local"
               value={form.expiry_at}
               onChange={(e) => setForm({ ...form, expiry_at: e.target.value })}
             />
             {form.expiry_at && (
               <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                 Hides after {new Date(form.expiry_at).toLocaleString('en-GB', {
                   day: '2-digit', month: '2-digit', year: 'numeric',
                   hour: '2-digit', minute: '2-digit',
                 })}
               </p>
             )}
           </Field>
         </div>

        <Field label="Attachment" hint="Optional - PDF, image or document">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              setAttachment(e.target.files?.[0] || null)
              if (e.target) e.target.value = ''
            }}
          />
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="h-4 w-4 mr-2" />
              {attachment ? 'Change file' : 'Choose file'}
            </Button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {attachment ? attachment.name : 'No file selected'}
            </span>
          </div>
          {attachment && (
            <p className="mt-1 text-xs text-green-600 dark:text-green-400">
              Selected: {attachment.name}
            </p>
          )}
          {announcement?.attachment_name && !attachment && (
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Current: {announcement.attachment_name}
            </p>
          )}
        </Field>

        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input
            type="checkbox"
            checked={form.is_pinned}
            onChange={(e) => setForm({ ...form, is_pinned: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Pin to top of the feed
        </label>
      </div>
    </Modal>
  )
}

type PaginatedCourses = { items: Course[] }