import { Link } from 'react-router-dom'
import { GraduationCap } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <div className="text-center">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <GraduationCap className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">Page not found</p>
        <Link to="/" className="inline-block px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Go Home
        </Link>
      </div>
    </div>
  )
}
