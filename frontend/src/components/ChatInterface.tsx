import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';

interface ChatSource {
  document_name: string;
  chunk_id: string;
}

interface ExtendedChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: ChatSource[];
}

export const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [provider, setProvider] = useState<'openai' | 'vllm' | 'gemini'>('gemini');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const {
    messages,
    sendMessage,
    isLoading,
    clearMessages
  } = useChat();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const message = input.trim();
    setInput('');
    await sendMessage(message, provider);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const providerConfigs = {
    gemini: { name: 'Google Gemini', color: 'bg-blue-600', icon: '✨' },
    openai: { name: 'OpenAI GPT', color: 'bg-green-600', icon: '🤖' },
    vllm: { name: 'VLLM Local', color: 'bg-purple-600', icon: '🏠' }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 h-[600px] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="text-xl">💬</div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              RAG Chat Interface
            </h2>
            <p className="text-sm text-gray-600">
              Ask questions about your uploaded documents
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Provider Selection */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Provider:</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as typeof provider)}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {Object.entries(providerConfigs).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.icon} {config.name}
                </option>
              ))}
            </select>
          </div>

          {/* Clear button */}
          <button
            onClick={clearMessages}
            disabled={messages.length === 0}
            className="text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl text-gray-400 mb-2">💭</div>
            <p className="text-gray-500 mb-2">Start a conversation</p>
            <p className="text-sm text-gray-400">
              Ask questions about your documents and get AI-powered answers
            </p>
            <div className="mt-4 space-y-2 text-sm text-gray-500">
              <p className="font-medium">Try asking:</p>
              <ul className="space-y-1 text-xs">
                <li>"What are the main topics in the documents?"</li>
                <li>"Summarize the key findings"</li>
                <li>"What conflicts were detected?"</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message: ExtendedChatMessage, index: number) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="text-sm">
                  {message.content}
                </div>
                {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <p className="text-xs text-gray-600 font-medium">Sources:</p>
                    <ul className="text-xs text-gray-600 mt-1 space-y-1">
                      {message.sources.map((source: ChatSource, idx: number) => (
                        <li key={idx}>
                          📄 {source.document_name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-xs">
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-gray-600 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm text-gray-600">
                  {providerConfigs[provider].icon} Thinking...
                </span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your documents..."
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={`px-4 py-2 text-white text-sm font-medium rounded-md transition-colors ${
              providerConfigs[provider].color
            } hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              'Send'
            )}
          </button>
        </form>
        
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <span className={`px-2 py-0.5 rounded text-white ${providerConfigs[provider].color}`}>
            {providerConfigs[provider].icon} {providerConfigs[provider].name}
          </span>
        </div>
      </div>
    </div>
  );
};
