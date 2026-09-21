import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { FileUpload } from '@/components/ui/file-upload'
import { Input } from '@/components/ui/input'
import { format } from 'date-fns'
import { FileDown, Clock, CheckCircle } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function StudentAssignments() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedAssignment, setSelectedAssignment] = useState<any>(null)
  const [submissionText, setSubmissionText] = useState('')
  const [submissionFile, setSubmissionFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['assignments'],
    queryFn: () => api.getAssignments(1, 50),
  })

  const filteredAssignments = (data?.items || []).filter((a: any) =>
    a.title.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleSubmit = async () => {
    if (!selectedAssignment) return

    setIsSubmitting(true)
    try {
      await api.submitAssignment(
        selectedAssignment.id,
        submissionText || undefined,
        submissionFile || undefined
      )
      toast.success('Assignment submitted successfully')
      queryClient.invalidateQueries({ queryKey: ['assignments'] })
      setSelectedAssignment(null)
      setSubmissionText('')
      setSubmissionFile(null)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to submit assignment')
    } finally {
      setIsSubmitting(false)
    }
  }

  const downloadAttachment = (assignment: any) => {
    if (assignment.attachment_path) {
      window.open(`/uploads/${assignment.attachment_path}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Assignments</h1>
        <Input
          placeholder="Search assignments..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {isLoading ? (
          <p className="text-gray-500 dark:text-gray-400">Loading assignments...</p>
        ) : filteredAssignments.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 col-span-2 text-center">
            No assignments found
          </p>
        ) : (
          filteredAssignments.map((a: any) => {
            const isOverdue = new Date(a.deadline) < new Date() && !a.my_submission
            const statusClass = a.my_submission
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : isOverdue
              ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'

            return (
              <div
                key={a.id}
                className={`rounded-xl p-6 border shadow-sm ${statusClass} cursor-pointer hover:shadow-md transition-shadow`}
                onClick={() => setSelectedAssignment(a)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{a.title}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{a.subject_name}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Max marks: {a.max_marks}
                    </p>
                  </div>
                  {a.my_submission && (
                    <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                  )}
                </div>

                <div className="flex items-center gap-4 mt-4">
                  <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                    <Clock className="w-4 h-4" />
                    <span>Due: {format(new Date(a.deadline), 'MMM dd, yyyy')}</span>
                  </div>
                  {a.attachment_name && (
                    <button
                      onClick={(e) => { e.stopPropagation(); downloadAttachment(a) }}
                      className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <FileDown className="w-4 h-4" />
                      {a.attachment_name}
                    </button>
                  )}
                </div>

                {a.my_submission && (
                  <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-700/50 rounded-lg">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Status: {a.my_submission.is_late ? 'Late submission' : 'On time'}
                    </p>
                    {a.my_submission.grade !== undefined && a.my_submission.grade !== null && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Grade: {a.my_submission.grade}/{a.max_marks}
                      </p>
                    )}
                    {a.my_submission.feedback && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        {a.my_submission.feedback}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {selectedAssignment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {selectedAssignment.title}
                </h2>
                <button
                  onClick={() => setSelectedAssignment(null)}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  ✕
                </button>
              </div>

              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {selectedAssignment.description}
              </p>

              {selectedAssignment.instructions && (
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-4">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-2">Instructions</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {selectedAssignment.instructions}
                  </p>
                </div>
              )}

                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                 <h3 className="font-medium text-gray-900 dark:text-white mb-3">Submit Assignment</h3>
                 <textarea
                   placeholder="Enter your submission..."
                   value={submissionText}
                   onChange={(e) => setSubmissionText(e.target.value)}
                   className="w-full h-32 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white resize-none"
                 />
                 <FileUpload
                   onFileSelect={setSubmissionFile}
                   maxSizeMB={10}
                   label="Upload file"
                 />
                <div className="flex items-center justify-between mt-4">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Max marks: {selectedAssignment.max_marks}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setSelectedAssignment(null)}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSubmit}
                      disabled={!submissionText && !submissionFile || isSubmitting}
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit'}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
