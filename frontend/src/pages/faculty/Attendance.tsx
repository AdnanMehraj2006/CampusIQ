import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { AttendanceRosterStudent } from '@/types'
import { Button } from '@/components/ui/button'
import { Check, X, Clock, Shield, RefreshCw } from 'lucide-react'
import { toast } from 'react-hot-toast'

type StudentRoster = AttendanceRosterStudent

export default function FacultyAttendance() {
  const queryClient = useQueryClient()
  const [subjectId, setSubjectId] = useState<number>()
  const [section, setSection] = useState<string>()
  const [date, setDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [selectedStudents, setSelectedStudents] = useState<Map<number, 'present' | 'absent' | 'late' | 'excused'>>(new Map())
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { data: dashboard, isLoading: loadingDashboard } = useQuery({
    queryKey: ['dashboard', 'faculty'],
    queryFn: () => api.getDashboard('faculty'),
  })

  const { data: roster, isLoading: loadingRoster, refetch } = useQuery({
    queryKey: ['attendance-roster', subjectId, section, date],
    queryFn: async () => {
      if (!subjectId || !section) return null
      return api.getAttendanceRoster(subjectId, section, date)
    },
    enabled: !!subjectId && !!section,
  })

  useEffect(() => {
    if (roster?.students) {
      const statuses = new Map<number, 'present' | 'absent' | 'late' | 'excused'>()
      roster.students.forEach((s: StudentRoster) => {
        if (s.status) {
          statuses.set(s.student_id, s.status)
        }
      })
      setSelectedStudents(statuses)
    }
  }, [roster])

  const handleMark = (studentId: number, status: 'present' | 'absent' | 'late' | 'excused') => {
    setSelectedStudents(prev => new Map(prev).set(studentId, status))
  }

  const handleMarkAllPresent = () => {
    const allPresent = new Map<number, 'present' | 'absent' | 'late' | 'excused'>()
    roster?.students.forEach((s: StudentRoster) => {
      allPresent.set(s.student_id, 'present')
    })
    setSelectedStudents(allPresent)
  }

  const handleSubmit = async () => {
    if (!subjectId || !section) return

    const marks = Array.from(selectedStudents.entries()).map(([studentId, status]) => ({
      student_id: studentId,
      status,
    }))

    if (marks.length === 0) {
      toast.error('No students marked for attendance')
      return
    }

    setIsSubmitting(true)
    try {
      await api.markAttendance(subjectId, section, date, marks)
      toast.success('Attendance marked successfully')
      queryClient.invalidateQueries({ queryKey: ['my-attendance'] })
      queryClient.invalidateQueries({ queryKey: ['attendance-roster'] })
      setSelectedStudents(new Map())
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to mark attendance')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Faculty Attendance</h1>

      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject</label>
            <select
              value={subjectId || ''}
              onChange={(e) => setSubjectId(e.target.value ? parseInt(e.target.value) : undefined)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">Select subject</option>
              {loadingDashboard ? (
                <option>Loading...</option>
              ) : (
                (dashboard as any).subjects?.map((s: any) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Section</label>
            <select
              value={section || ''}
              onChange={(e) => setSection(e.target.value || undefined)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">Select section</option>
              {subjectId && !loadingDashboard && (
                ['A', 'B', 'C', 'D'].map(sec => (
                  <option key={sec} value={sec}>{sec}</option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={() => refetch()} disabled={!subjectId || !section}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Load Roster
          </Button>
        </div>
      </div>

      {subjectId && section && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">Attendance Roster</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {date} • Section {section}
              </p>
            </div>
            <Button onClick={handleMarkAllPresent} disabled={!subjectId || !section} className="bg-green-600 hover:bg-green-700">
              <Check className="w-4 h-4 mr-2" />
              Mark All Present
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Student</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Enrollment</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {loadingRoster ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                      Loading roster...
                    </td>
                  </tr>
                ) : roster?.students.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                      No students found in this section
                    </td>
                  </tr>
                ) : (
                  roster?.students.map((student: StudentRoster) => {
                    const currentStatus = selectedStudents.get(student.student_id) || 'absent'
                    return (
                      <tr key={student.student_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                        <td className="px-6 py-4">
                          <p className="font-medium text-gray-900 dark:text-white">{student.name}</p>
                        </td>
                        <td className="px-6 py-4 text-gray-500 dark:text-gray-400">
                          {student.enrollment_number}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-2">
                            {(['present', 'absent', 'late', 'excused'] as const).map((s) => (
                              <button
                                key={s}
                                onClick={() => handleMark(student.student_id, s)}
                                className={`p-2 rounded-lg border-2 transition-colors
                                  ${currentStatus === s 
                                    ? (s === 'present' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800' 
                                       : s === 'absent' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
                                       : s === 'late' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800'
                                       : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800')
                                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                                  }`}
                                title={s.charAt(0).toUpperCase() + s.slice(1)}
                              >
                                {s === 'present' && <Check className="w-4 h-4" />}
                                {s === 'absent' && <X className="w-4 h-4" />}
                                {s === 'late' && <Clock className="w-4 h-4" />}
                                {s === 'excused' && <Shield className="w-4 h-4" />}
                              </button>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {selectedStudents.size} / {roster?.students.length || 0} students marked
              </p>
            </div>
            <Button onClick={handleSubmit} disabled={selectedStudents.size === 0 || isSubmitting || !subjectId || !section} className="bg-green-600 hover:bg-green-700">
              {isSubmitting ? 'Submitting...' : 'Submit Attendance'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
