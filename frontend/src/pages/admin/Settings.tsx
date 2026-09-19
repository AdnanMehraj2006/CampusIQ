import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getApiErrorMessage } from '@/lib/api'
import { SystemSetting } from '@/types'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { LoadingState, ErrorState } from '@/components/ui/states'
import { Save } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useState } from 'react'

const CATEGORY_LABELS: Record<string, string> = {
  attendance: 'Attendance',
  files: 'Files',
  ai: 'AI Assistant',
  general: 'General',
}

export default function AdminSettings() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery<SystemSetting[]>({
    queryKey: ['system-settings'],
    queryFn: () => api.getSettings(),
  })

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => api.updateSetting(key, value),
    onSuccess: () => {
      toast.success('Setting updated')
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, 'Failed to update setting')),
  })

  if (isLoading) return <LoadingState message="Loading settings..." />
  if (isError) return <ErrorState message="Failed to load settings" onRetry={refetch} />

  const grouped = (data || []).reduce<Record<string, SystemSetting[]>>((acc, s) => {
    const cat = s.category || 'general'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(s)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <PageHeader title="System Settings" subtitle="Institution-wide configuration values" />

      {Object.entries(grouped).map(([category, settings]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle>{CATEGORY_LABELS[category] || category}</CardTitle>
            <CardDescription>{settings.length} setting(s)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {settings.map((s) => (
              <SettingRow
                key={s.key}
                setting={s}
                onSave={(value) => updateMutation.mutate({ key: s.key, value })}
                saving={updateMutation.isPending}
              />
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function SettingRow({
  setting,
  onSave,
  saving,
}: {
  setting: SystemSetting
  onSave: (value: string) => void
  saving: boolean
}) {
  const [value, setValue] = useState(setting.value)
  const dirty = value !== setting.value

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
      <div className="flex-1 space-y-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {setting.key.replace(/_/g, ' ')}
        </label>
        {setting.description && (
          <p className="text-xs text-gray-500 dark:text-gray-400">{setting.description}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="sm:w-40"
          aria-label={setting.key}
        />
        <Button size="sm" onClick={() => onSave(value)} disabled={!dirty || saving}>
          <Save className="mr-1 h-4 w-4" />
          Save
        </Button>
      </div>
    </div>
  )
}

type ApiErrorShape = { data?: { detail?: string } }
