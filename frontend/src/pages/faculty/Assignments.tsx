import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { format } from 'date-fns'
import { FileDown, Clock, CheckCircle, X, Plus, Trash2 } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function FacultyAssignments() {
  const queryClient = useQueryClient()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedAssignment, setSelectedAssignment] = useState<any>(null)
  const [selectedSubmission, setSelectedSubmission] = useState<any>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['my-assignments'],
    queryFn: () => api.getAssignments(1, 50),
  })

  const { data: submissionsData } = useQuery({
    queryKey: ['submissions', selectedAssignment?.id],
    queryFn: () => selectedAssignment && api.getSubmissions(selectedAssignment.id, 1, 100),
    enabled: !!selectedAssignment,
  })

  const handleSubmit = async (data: any) => {
    try {
      await api.createAssignment(data)
      toast.success('Assignment created successfully')
      queryClient.invalidateQueries({ queryKey: ['my-assignments'] })
      setShowCreateForm(false)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to create assignment')
    }
  }

  const handleUpdate = async (data: any) => {
    try {
      await api.updateAssignment(selectedAssignment.id, data)
      toast.success('Assignment updated successfully')
      queryClient.invalidateQueries({ queryKey: ['my-assignments'] })
      setSelectedAssignment(null)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to update assignment')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this assignment?')) return
    try {
      await api.deleteAssignment(id)
      toast.success('Assignment deleted')
      queryClient.invalidateQueries({ queryKey: ['my-assignments'] })
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to delete assignment')
    }
  }

  const handleGrade = async (submissionId: number, grade: number, feedback: string) => {
    try {
      await api.gradeSubmission(submissionId, grade, feedback)
      toast.success('Grade submitted successfully')
      queryClient.invalidateQueries({ queryKey: ['submissions', selectedAssignment?.id] })
      setSelectedSubmission(null)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to submit grade')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Assignments</h1>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Create Assignment
        </Button>
      </div>

      {showCreateForm && (
        <AssignmentForm
          onSubmit={handleSubmit}
          onCancel={() => setShowCreateForm(false)}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {isLoading ? (
          <p className="text-gray-500 dark:text-gray-400">Loading assignments...</p>
        ) : (data?.items || []).length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 col-span-2 text-center">
            No assignments created yet
          </p>
        ) : (
          (data?.items || []).map((a: any) => (
            <div
              key={a.id}
              className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => setSelectedAssignment(a)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{a.title}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {a.subject_name}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {a.submission_count || 0} submissions
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(a.id) }}
                  className="text-red-500 hover:text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center gap-2 mt-4">
                <Clock className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Due: {format(new Date(a.deadline), 'MMM dd, yyyy')}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {selectedAssignment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {selectedAssignment.title}
                </h2>
                <button
                  onClick={() => setSelectedAssignment(null)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mb-6">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">Details</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-2">
                  {selectedAssignment.description}
                </p>
                {selectedAssignment.instructions && (
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 dark:text-white mb-1">Instructions</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {selectedAssignment.instructions}
                    </p>
                  </div>
                )}
              </div>

              <div>
                <h3 className="font-medium text-gray-900 dark:text-white mb-4">Submissions</h3>
                <div className="space-y-3">
                  {(!submissionsData?.items || submissionsData?.items.length === 0) ? (
                    <p className="text-gray-500 dark:text-gray-400">No submissions yet</p>
                  ) : (
                    submissionsData?.items.map((s: any) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{s.student_name}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {s.submitted_at ? `Submitted: ${format(new Date(s.submitted_at), 'MMM dd, yyyy HH:mm')}` : 'Not submitted'}
                          </p>
                          {s.is_late && (
                            <span className="text-xs text-red-600 dark:text-red-400">Late</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {s.grade !== null && s.grade !== undefined ? (
                            <span className="text-sm font-medium text-green-600 dark:text-green-400">
                              {s.grade}/{selectedAssignment.max_marks}
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => setSelectedSubmission(s)}
                            >
                              Grade
                            </Button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedSubmission && (
        <GradeForm
          submission={selectedSubmission}
          maxMarks={selectedAssignment.max_marks}
          onSubmit={handleGrade}
          onCancel={() => setSelectedSubmission(null)}
        />
      )}
    </div>
  )
}

function AssignmentForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: any) => void
  onCancel: () => void
}) {
  const [data, setData] = useState({
    title: '',
    description: '',
    instructions: '',
    subject_id: '',
    section: '',
    deadline: '',
    max_marks: 100,
    allow_late: false,
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Create Assignment
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
              <Input
                value={data.title}
                onChange={(e) => setData({ ...data, title: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
              <textarea
                value={data.description}
                onChange={(e) => setData({ ...data, description: e.target.value })}
                className="w-full h-24 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Instructions</label>
              <textarea
                value={data.instructions}
                onChange={(e) => setData({ ...data, instructions: e.target.value })}
                className="w-full h-24 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject</label>
                <select
                  value={data.subject_id}
                  onChange={(e) => setData({ ...data, subject_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white"
                >
                  <option value="">Select subject</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Section</label>
                <Input
                  value={data.section}
                  onChange={(e) => setData({ ...data, section: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Deadline</label>
                <Input
                  type="datetime-local"
                  value={data.deadline}
                  onChange={(e) => setData({ ...data, deadline: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Max Marks</label>
                <Input
                  type="number"
                  value={data.max_marks}
                  onChange={(e) => setData({ ...data, max_marks: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={() => onSubmit(data)}>Create</Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function GradeForm({
  submission,
  maxMarks,
  onSubmit,
  onCancel,
}: {
  submission: any
  maxMarks: number
  onSubmit: (submissionId: number, grade: number, feedback: string) => void
  onCancel: () => void
}) {
  const [grade, setGrade] = useState(submission.grade?.toString() || '')
  const [feedback, setFeedback] = useState(submission.feedback || '')

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-xl w-full mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Grade Submission
          </h2>
          <div className="mb-4">
            <p className="text-gray-600 dark:text-gray-400">Student: {submission.student_name}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {submission.submitted_at && `Submitted: ${format(new Date(submission.submitted_at), 'MMM dd, yyyy HH:mm')}`}
            </p>
            {submission.text_submission && (
              <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">{submission.text_submission}</p>
              </div>
            )}
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Grade (out of {maxMarks})</label>
              <Input
                type="number"
                min={0}
                max={maxMarks}
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Feedback</label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className="w-full h-24 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white resize-none"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={() => onSubmit(submission.id, parseInt(grade) || 0, feedback)}>
              Submit Grade
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
