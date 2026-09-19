import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function Marks() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['my-marks'],
    queryFn: () => api.getMyMarks(1, 500),
  })

  const handleSubmit = async (data: any) => {
    try {
      await api.createMark(data)
      toast.success('Marks submitted successfully')
      queryClient.invalidateQueries({ queryKey: ['marks'] })
      setShowForm(false)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to submit marks')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Marks</h1>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Enter Marks
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Subject</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Assessment</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Marks</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Percentage</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Remarks</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  Loading marks...
                </td>
              </tr>
            ) : (data?.items || []).length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No marks recorded yet
                </td>
              </tr>
            ) : (
              (data?.items || []).map((m: any) => (
                <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-900 dark:text-white">{m.subject_name}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-gray-900 dark:text-white">{m.title}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{m.assessment_type}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {m.marks}/{m.max_marks}
                    </p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${m.percentage >= 60 ? 'bg-green-500' : m.percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${m.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-900 dark:text-white">{m.percentage.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {m.remarks || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <MarkForm
          onSubmit={handleSubmit}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  )
}

function MarkForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: any) => void
  onCancel: () => void
}) {
  const [data, setData] = useState({
    student_id: '',
    subject_id: '',
    assessment_type: 'internal',
    title: '',
    marks: '',
    max_marks: '100',
    remarks: '',
  })

  const marksPercentage = data.marks && data.max_marks 
    ? (parseFloat(data.marks) / parseFloat(data.max_marks) * 100).toFixed(1) 
    : '0'

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-xl w-full mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Enter Marks
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Student ID</label>
              <Input
                value={data.student_id}
                onChange={(e) => setData({ ...data, student_id: e.target.value })}
                placeholder="Enter student ID"
              />
            </div>
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
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Assessment Type</label>
              <select
                value={data.assessment_type}
                onChange={(e) => setData({ ...data, assessment_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white"
              >
                <option value="internal">Internal Assessment</option>
                <option value="midterm">Midterm</option>
                <option value="final">Final</option>
                <option value="quiz">Quiz</option>
                <option value="assignment">Assignment</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
              <Input
                value={data.title}
                onChange={(e) => setData({ ...data, title: e.target.value })}
                placeholder="Exam/Quiz title"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Marks Obtained</label>
                <Input
                  type="number"
                  min={0}
                  value={data.marks}
                  onChange={(e) => setData({ ...data, marks: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Maximum Marks</label>
                <Input
                  type="number"
                  min={1}
                  value={data.max_marks}
                  onChange={(e) => setData({ ...data, max_marks: e.target.value })}
                />
              </div>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Percentage: <span className="font-medium">{marksPercentage}%</span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Remarks</label>
              <textarea
                value={data.remarks}
                onChange={(e) => setData({ ...data, remarks: e.target.value })}
                className="w-full h-16 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-gray-900 dark:text-white resize-none"
                placeholder="Optional comments"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={() => onSubmit(data)}>Submit</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
