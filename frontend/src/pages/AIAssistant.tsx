import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, Trash2, Sparkles } from 'lucide-react'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { data: suggestions } = useQuery({
    queryKey: ['ai-suggestions'],
    queryFn: () => api.getAISuggestions(),
  })

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    const userMessage: ChatMessage = { role: 'user', content }
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsProcessing(true)

    try {
      const response = await api.chat(content, messages)
      const assistantMessage: ChatMessage = { 
        role: 'assistant', 
        content: response.response 
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Sorry, I'm having trouble connecting right now. Please try again later.`
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsProcessing(false)
    }
  }

  const clearConversation = () => {
    setMessages([])
    setInputValue('')
  }

  return (
    <div className="h-[calc(100vh-200px)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            AI Assistant
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Ask questions about your academic progress, schedule, and more
          </p>
        </div>
        {messages.length > 0 && (
          <Button variant="outline" onClick={clearConversation}>
            <Trash2 className="w-4 h-4 mr-2" />
            Clear conversation
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Sparkles className="w-12 h-12 mx-auto text-blue-600 dark:text-blue-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                How can I help you today?
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                Try asking about your attendance, schedule, or assignments
              </p>
              {suggestions && suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.map((s: any, index: number) => (
                    <button
                      key={index}
                      onClick={() => sendMessage(s.question)}
                      className="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg text-sm hover:bg-blue-100 dark:hover:bg-blue-900/30"
                    >
                      {s.question}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-xl p-4 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="mt-4">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage(inputValue)
              }
            }}
            placeholder="Type your message..."
            disabled={isProcessing}
          />
          <Button
            onClick={() => sendMessage(inputValue)}
            disabled={isProcessing || !inputValue.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
