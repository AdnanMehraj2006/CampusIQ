import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { AttendanceAnalytics, AttendancePrediction } from '@/types'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Minus, AlertTriangle, CheckCircle } from 'lucide-react'

interface ZoneIconProps {
  zone: 'safe' | 'warning' | 'critical' | 'none'
  colors: Record<string, string>
}

function ZoneIcon({ zone, colors }: ZoneIconProps) {
  const Icon = {
    safe: CheckCircle,
    warning: AlertTriangle,
    critical: AlertTriangle,
    none: Minus,
  }[zone]
  
  return <Icon className="w-6 h-6" style={{ color: colors[zone] }} />
}

export default function StudentAttendance() {
  const { data: analytics, isLoading: loadingAnalytics } = useQuery<AttendanceAnalytics>({
    queryKey: ['my-attendance'],
    queryFn: () => api.getMyAttendance(),
  })

  const { data: prediction, isLoading: loadingPrediction } = useQuery<AttendancePrediction>({
    queryKey: ['attendance-prediction'],
    queryFn: () => api.getAttendancePredictions(75),
  })

  if (loadingAnalytics || loadingPrediction) {
    return <div className="text-center py-12">Loading...</div>
  }

  const colors = {
    safe: '#22c55e',
    warning: '#f59e0b',
    critical: '#ef4444',
    none: '#9ca3af',
  }

  const zoneIcons = {
    safe: CheckCircle,
    warning: AlertTriangle,
    critical: AlertTriangle,
    none: Minus,
  }

  const trendData = analytics?.trend.map(t => ({
    date: new Date(t.date).toLocaleDateString(),
    percentage: t.percentage,
  })) || []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Attendance</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">Overall Attendance</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{analytics?.overall_percentage?.toFixed(1)}%</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {analytics?.classes_attended} / {analytics?.classes_conducted} classes
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">Attendance Zone</p>
           <div className="flex items-center gap-2 mt-2">
             <ZoneIcon zone={analytics?.zone || 'none'} colors={colors} />
             <p className="text-2xl font-bold text-gray-900 dark:text-white">
               {analytics?.zone?.toUpperCase()}
             </p>
           </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Required: {analytics?.required_percentage?.toFixed(0)}%
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">Classes Attended</p>
          <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-2">
            {analytics?.classes_attended}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {analytics?.late} late, {analytics?.excused} excused
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">Classes Missed</p>
          <p className="text-3xl font-bold text-red-600 dark:text-red-400 mt-2">
            {analytics?.absent}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {analytics?.total_classes - analytics?.classes_conducted} conducted
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Subject-wise Attendance</h2>
          <div className="space-y-3">
            {analytics?.subject_wise.map((subject) => (
              <div key={subject.subject_id} className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">{subject.subject_name}</p>
                  <div className="mt-1 w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full"
                      style={{ 
                        width: `${subject.percentage}%`,
                        backgroundColor: subject.percentage >= 75 ? '#22c55e' : subject.percentage >= 60 ? '#f59e0b' : '#ef4444'
                      }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{subject.percentage.toFixed(1)}%</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {subject.attended}/{subject.conducted}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Attendance Trend</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData}>
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  interval={0}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1f2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="percentage" radius={[4, 4, 0, 0]}>
                  {trendData.map((entry, index) => (
                    <Cell 
                      key={index} 
                      fill={entry.percentage >= 75 ? '#22c55e' : entry.percentage >= 60 ? '#f59e0b' : '#ef4444'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Attendance Prediction</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <p className="text-sm text-gray-500 dark:text-gray-400">Current Percentage</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
              {prediction?.current_percentage?.toFixed(1)}%
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <p className="text-sm text-gray-500 dark:text-gray-400">Required to Pass</p>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-2">
              {prediction?.required_percentage?.toFixed(0)}%
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <p className="text-sm text-gray-500 dark:text-gray-400">Classes Needed</p>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-2">
              {prediction?.classes_needed_to_pass}
            </p>
          </div>
        </div>
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-800 dark:text-blue-200 text-center">
            {prediction?.prediction || 'Keep up your current attendance to stay in good standing.'}
          </p>
        </div>
      </div>
    </div>
  )
}
