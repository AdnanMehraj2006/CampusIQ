import { useState, useRef } from 'react'
import { Button } from './button'
import { toast } from 'react-hot-toast'
import { Upload, X } from 'lucide-react'

export interface FileUploadProps {
  onFileSelect: (file: File | null) => void
  accept?: string
  maxSizeMB?: number
  label?: string
  disabled?: boolean
}

export function FileUpload({ onFileSelect, accept = '*/*', maxSizeMB = 10, label = 'Choose file', disabled }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const validateFile = (file: File): boolean => {
    if (file.size > maxSizeMB * 1024 * 1024) {
      toast.error(`File too large: ${(file.size / (1024 * 1024)).toFixed(1)} MB exceeds the maximum allowed size of ${maxSizeMB} MB.`)
      return false
    }
    return true
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    if (!file) {
      setSelectedFile(null)
      onFileSelect(null)
      return
    }
    if (validateFile(file)) {
      setSelectedFile(file)
      onFileSelect(file)
    } else {
      e.target.value = ''
      setSelectedFile(null)
      onFileSelect(null)
    }
  }

  const handleClear = () => {
    setSelectedFile(null)
    onFileSelect(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleFileChange}
          disabled={disabled}
          className="hidden"
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          {label}
        </Button>
        {selectedFile && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={disabled}
            className="flex items-center gap-1 text-gray-500"
          >
            <X className="w-4 h-4" />
            Clear
          </Button>
        )}
      </div>
      {selectedFile && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)
        </div>
      )}
    </div>
  )
}
