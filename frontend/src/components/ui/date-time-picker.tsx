import { useState } from 'react'

export interface DateTimePickerProps {
  value: string
  onChange: (value: string) => void
  label?: string
  disabled?: boolean
}

export function DateTimePicker({ value, onChange, label = 'Date and time', disabled }: DateTimePickerProps) {
  const [date, setDate] = useState('')
  const [hour, setHour] = useState('')
  const [minute, setMinute] = useState('')
  const [ampm, setAmpm] = useState('AM')

  const parseValue = (val: string) => {
    if (!val) {
      setDate('')
      setHour('')
      setMinute('')
      setAmpm('AM')
      return
    }
    const d = new Date(val)
    setDate(d.toISOString().slice(0, 10))

    let h = d.getHours()
    const m = d.getMinutes()
    const isPM = h >= 12

    setAmpm(isPM ? 'PM' : 'AM')
    setMinute(m.toString().padStart(2, '0'))

    if (h === 0) {
      setHour('12')
    } else if (h > 12) {
      setHour((h - 12).toString().padStart(2, '0'))
    } else {
      setHour(h.toString().padStart(2, '0'))
    }
  }

  const buildValue = () => {
    if (!date || !hour || !minute) return ''
    const d = new Date(date)
    let h = parseInt(hour, 10)

    if (ampm === 'PM' && h !== 12) h += 12
    if (ampm === 'AM' && h === 12) h = 0

    d.setHours(h, parseInt(minute, 10), 0, 0)
    return d.toISOString()
  }

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDate = e.target.value
    setDate(newDate)
    if (newDate && hour && minute) {
      onChange(buildValue())
    }
  }

  const handleHourChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newHour = e.target.value
    setHour(newHour)
    if (date && newHour && minute) {
      onChange(buildValue())
    }
  }

  const handleMinuteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newMinute = e.target.value
    setMinute(newMinute)
    if (date && hour && newMinute) {
      onChange(buildValue())
    }
  }

  const handleAmpmChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newAmpm = e.target.value
    setAmpm(newAmpm)
    if (date && hour && minute) {
      onChange(buildValue())
    }
  }

  const minutes = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0'))

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Date (DD-MM-YYYY)
          </label>
          <input
            type="date"
            value={date}
            onChange={handleDateChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Hour
          </label>
          <select
            value={hour}
            onChange={handleHourChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="">--</option>
            {Array.from({ length: 12 }, (_, i) => {
              const h = (i + 1).toString().padStart(2, '0')
              return (
                <option key={h} value={h}>
                  {h}
                </option>
              )
            })}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Minute
          </label>
          <select
            value={minute}
            onChange={handleMinuteChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="">--</option>
            {minutes.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Period
          </label>
          <select
            value={ampm}
            onChange={handleAmpmChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="AM">AM</option>
            <option value="PM">PM</option>
          </select>
        </div>
      </div>
      {date && hour && minute && (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Selected: {new Date(buildValue()).toLocaleString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      )}
    </div>
  )
}
