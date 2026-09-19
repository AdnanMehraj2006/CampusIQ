import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { getRole } from '@/lib/auth'
import { SearchResult } from '@/types'
import { Search, X, User, BookOpen, FileText, Megaphone, FolderKanban, Building2, GraduationCap } from 'lucide-react'

const TYPE_META: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; label: string; route: string }
> = {
  student: { icon: GraduationCap, label: 'Students', route: 'students' },
  faculty: { icon: User, label: 'Faculty', route: 'faculty' },
  subject: { icon: BookOpen, label: 'Subjects', route: 'subjects' },
  department: { icon: Building2, label: 'Departments', route: 'departments' },
  assignment: { icon: FileText, label: 'Assignments', route: 'assignments' },
  project: { icon: FolderKanban, label: 'Projects', route: 'projects' },
  announcement: { icon: Megaphone, label: 'Announcements', route: 'announcements' },
}

const RESULT_ROUTE: Record<string, string> = {
  announcement: 'announcements',
  project: 'projects',
  assignment: 'assignments',
}

export function GlobalSearch() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const role = getRole()

  const { data, isFetching } = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: () => api.search(debounced, undefined, 1, 20),
    enabled: debounced.length >= 2,
  })

  // Debounce the input so we don't hammer the API on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250)
    return () => clearTimeout(timer)
  }, [query])

  // Cmd/Ctrl + K opens the search.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(true)
      } else if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (open) inputRef.current?.focus()
    else setQuery('')
  }, [open])

  const basePath = role ? `/${role.toLowerCase()}` : ''

  const handleSelect = (result: SearchResult) => {
    const section = RESULT_ROUTE[result.type]
    setOpen(false)
    if (section) {
      navigate(`${basePath}/${section}`)
    } else {
      const fallback = TYPE_META[result.type]?.route
      if (fallback) navigate(`${basePath}/${fallback}`)
    }
  }

  const results = data?.items || []
  const grouped = results.reduce<Record<string, SearchResult[]>>((acc, r) => {
    if (!acc[r.type]) acc[r.type] = []
    acc[r.type].push(r)
    return acc
  }, {})

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex h-9 w-full items-center gap-2 rounded-lg border border-gray-300 bg-transparent px-3 text-sm text-gray-400 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-800 sm:w-64"
        aria-label="Search"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Search...</span>
        <kbd className="ml-auto hidden rounded border border-gray-300 px-1.5 text-xs text-gray-400 dark:border-gray-600 sm:inline">
          Ctrl K
        </kbd>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} aria-hidden="true" />
          <div className="relative w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl dark:bg-gray-800">
            <div className="flex items-center gap-2 border-b border-gray-200 p-3 dark:border-gray-700">
              <Search className="h-5 w-5 shrink-0 text-gray-400" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search students, faculty, subjects, assignments, projects, announcements..."
                className="flex-1 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400 dark:text-white"
              />
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
                aria-label="Close search"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="max-h-[60vh] overflow-y-auto p-2">
              {debounced.length < 2 ? (
                <p className="px-3 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Type at least 2 characters to search
                </p>
              ) : isFetching ? (
                <p className="px-3 py-8 text-center text-sm text-gray-500 dark:text-gray-400">Searching...</p>
              ) : results.length === 0 ? (
                <p className="px-3 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  No results for &ldquo;{debounced}&rdquo;
                </p>
              ) : (
                Object.entries(grouped).map(([type, items]) => {
                  const meta = TYPE_META[type] || {
                    icon: FileText,
                    label: type,
                    route: '',
                  }
                  const Icon = meta.icon
                  return (
                    <div key={type} className="mb-2">
                      <p className="px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        {meta.label}
                      </p>
                      {items.map((r) => (
                        <button
                          key={`${r.type}-${r.id}`}
                          onClick={() => handleSelect(r)}
                          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          <Icon className="h-4 w-4 shrink-0 text-gray-400" />
                          <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900 dark:text-white">
                            {r.title}
                          </span>
                          <span className="shrink-0 truncate text-xs text-gray-500 dark:text-gray-400">
                            {r.subtitle}
                          </span>
                        </button>
                      ))}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
