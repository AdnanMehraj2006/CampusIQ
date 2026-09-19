import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Plus, Edit2, Trash2 } from 'lucide-react'
import { toast } from 'react-hot-toast'

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function AdminTimetable() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [entryData, setEntryData] = useState({
    day: 'Monday',
    period: 1,
    start_time: '09:00',
    end_time: '10:00',
    subject_id: '',
    faculty_id: '',
    classroom_id: '',
    section: 'A',
    semester_id: '',
  })
  const [editingEntry, setEditingEntry] = useState<any>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['all-timetable'],
    queryFn: () => api.getAllTimetableEntries(1, 500),
  })

  const handleSubmit = async (data: any) => {
    try {
      await api.createTimetableEntry(data)
      toast.success('Timetable entry created')
      queryClient.invalidateQueries({ queryKey: ['all-timetable'] })
      setShowForm(false)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to create entry')
    }
  }

  const handleUpdate = async (entryId: number, data: any) => {
    try {
      await api.updateTimetableEntry(entryId, data)
      toast.success('Timetable entry updated')
      queryClient.invalidateQueries({ queryKey: ['all-timetable'] })
      setEditingEntry(null)
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to update entry')
    }
  }

  const handleDelete = async (entryId: number) => {
    if (!confirm('Are you sure? This cannot be undone.')) return
    try {
      await api.deleteTimetableEntry(entryId)
      toast.success('Entry deleted')
      queryClient.invalidateQueries({ queryKey: ['all-timetable'] })
    } catch (error: any) {
      toast.error(error.data?.detail || 'Failed to delete entry')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Timetable Management</h1>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Entry
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Day</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Subject</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Faculty</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Section</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Room</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  Loading...
                </td>
              </tr>
            ) : (data?.items || []).length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No timetable entries yet
                </td>
              </tr>
            ) : (
              (data?.items || []).map((entry: any) => (
                <tr key={entry.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-6 py-4">{entry.day}</td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-900 dark:text-white">{entry.start_time}</span>
                    <span className="text-gray-400"> - </span>
                    <span className="text-sm text-gray-900 dark:text-white">{entry.end_time}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{entry.subject_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{entry.faculty_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{entry.section}</td>
                  <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">{entry.room_number || '-'}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setEditingEntry(entry)}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-700"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="text-red-600 dark:text-red-400 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <TimetableForm
          data={entryData}
          onChange={setEntryData}
          onSubmit={() => handleSubmit(entryData)}
          onCancel={() => setShowForm(false)}
        />
      )}

      {editingEntry && (
        <TimetableForm
          data={editingEntry}
          onChange={setEditingEntry}
          onSubmit={() => handleUpdate(editingEntry.id, editingEntry)}
          onCancel={() => setEditingEntry(null)}
          isEditing
        />
      )}
    </div>
  )
}

function TimetableForm({
  data,
  onChange,
  onSubmit,
  onCancel,
  isEditing,
}: {
  data: any
  onChange: (data: any) => void
  onSubmit: () => void
  onCancel: () => void
  isEditing?: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl max-w-xl w-full mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            {isEditing ? 'Edit Timetable Entry' : 'Add Timetable Entry'}
          </h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Day</label>
              <select
                value={data.day}
                onChange={(e) => onChange({ ...data, day: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {days.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Period</label>
              <Input
                type="number"
                value={String(data.period)}
                onChange={(e) => onChange({ ...data, period: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start Time</label>
              <Input
                type="time"
                value={data.start_time}
                onChange={(e) => onChange({ ...data, start_time: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End Time</label>
              <Input
                type="time"
                value={data.end_time}
                onChange={(e) => onChange({ ...data, end_time: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Section</label>
              <Input
                value={data.section}
                onChange={(e) => onChange({ ...data, section: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Subject ID</label>
              <Input
                type="number"
                value={String(data.subject_id)}
                onChange={(e) => onChange({ ...data, subject_id: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Faculty ID</label>
              <Input
                type="number"
                value={String(data.faculty_id)}
                onChange={(e) => onChange({ ...data, faculty_id: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Classroom ID</label>
              <Input
                type="number"
                value={String(data.classroom_id)}
                onChange={(e) => onChange({ ...data, classroom_id: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={onSubmit}>{isEditing ? 'Update' : 'Add'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
