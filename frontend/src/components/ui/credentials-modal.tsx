import { Modal } from './modal'
import { Button } from './button'
import { KeyRound, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'react-hot-toast'

export interface CreatedCredentials {
  name: string
  identifier: string
  password: string
}

/**
 * Shown exactly once after an account is created with a server-generated
 * password. Only the hash is stored; this is the only time the plaintext is
 * surfaced so the admin can share it securely.
 */
export function CredentialsModal({
  credentials,
  onClose,
}: {
  credentials: CreatedCredentials | null
  onClose: () => void
}) {
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (label: string, value: string) => {
    navigator.clipboard?.writeText(value)
    setCopied(label)
    toast.success(`${label} copied`)
    setTimeout(() => setCopied(null), 1500)
  }

  return (
    <Modal
      open={credentials !== null}
      onClose={onClose}
      title="Account credentials"
      description="A temporary password was generated automatically. Share it securely with the account owner."
      size="sm"
      footer={
        <Button onClick={onClose}>Done</Button>
      }
    >
      {credentials && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
            <KeyRound className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              This password is shown <strong>only once</strong>. The account can
              log in immediately. Please share it privately and ask the owner to
              change it after first login.
            </span>
          </div>

          <div className="space-y-2">
            <CredentialRow label="Name" value={credentials.name} />
            <CredentialRow
              label="Email / College ID"
              value={credentials.identifier}
              onCopy={() => copy('Identifier', credentials.identifier)}
              copied={copied === 'Identifier'}
            />
            <CredentialRow
              label="Temporary password"
              value={credentials.password}
              mono
              onCopy={() => copy('Password', credentials.password)}
              copied={copied === 'Password'}
            />
          </div>
        </div>
      )}
    </Modal>
  )
}

function CredentialRow({
  label,
  value,
  mono,
  onCopy,
  copied,
}: {
  label: string
  value: string
  mono?: boolean
  onCopy?: () => void
  copied?: boolean
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <code
          className={`flex-1 truncate rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 ${
            mono ? 'font-mono' : ''
          }`}
        >
          {value}
        </code>
        {onCopy && (
          <button
            type="button"
            onClick={onCopy}
            className="rounded-lg border border-gray-300 p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            aria-label={`Copy ${label}`}
          >
            {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  )
}
