import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createChatSession, listChatSessions, sendMessage as apiSendMessage, getChatMessages, ChatSession, ChatMessage } from '../api/chat';

interface ChatSource {
  document_name: string;
  chunk_id: string;
}

interface ExtendedChatMessage extends Omit<ChatMessage, 'id' | 'created_at'> {
  sources?: ChatSource[];
}

export function useChatSessions() {
  return useQuery<ChatSession[], Error>({
    queryKey: ['chat-sessions'],
    queryFn: () => listChatSessions(),
  });
}

export function useCreateChatSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name?: string) => createChatSession(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chat-sessions'] });
    },
  });
}

export function useChatMessages(sessionId: string) {
  return useQuery<ChatMessage[], Error>({
    queryKey: ['chat-messages', sessionId],
    queryFn: () => getChatMessages(sessionId),
    enabled: !!sessionId,
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) => 
      apiSendMessage(sessionId, content),
    onSuccess: (_, { sessionId }) => {
      qc.invalidateQueries({ queryKey: ['chat-messages', sessionId] });
    },
  });
}

// Simple chat hook for the chat interface
export const useChat = () => {
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const createSession = useCallback(async () => {
    try {
      const response = await createChatSession();
      setSessionId(response.session_id);
      return response.session_id;
    } catch (error) {
      console.error('Failed to create chat session:', error);
      throw error;
    }
  }, []);

  const sendMessage = useCallback(async (content: string, provider: string = 'openai') => {
    if (!content.trim()) return;

    setIsLoading(true);
    
    // Add user message immediately
    const userMessage: ExtendedChatMessage = {
      role: 'user',
      content: content.trim()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      // Create session if needed
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        currentSessionId = await createSession();
      }

      // Send message to API
      const response = await apiSendMessage(currentSessionId, content, provider);
      console.log('Full API response:', response);
      
      // Find the assistant's response (should be the last message)
      const assistantMessage = response.messages[response.messages.length - 1];
      
      if (assistantMessage && assistantMessage.role === 'assistant') {
        // Parse sources from response
        const sources: ChatSource[] = [];
        if (response.sources && Array.isArray(response.sources)) {
          console.log('Raw sources from API:', response.sources);
          
          // Use Set to remove duplicate document names
          const uniqueDocNames = new Set<string>();
          response.sources.forEach((source: any) => {
            if (source.document_name && typeof source.document_name === 'string') {
              uniqueDocNames.add(source.document_name);
            }
          });
          
          // Convert back to array format
          uniqueDocNames.forEach(docName => {
            sources.push({
              document_name: docName,
              chunk_id: ''
            });
          });
          
          console.log('Parsed sources (deduplicated):', sources);
        }
        
        const extendedMessage: ExtendedChatMessage = {
          role: assistantMessage.role,
          content: assistantMessage.content,
          sources: sources.length > 0 ? sources : undefined
        };
        
        console.log('Final message with sources:', extendedMessage);
        setMessages(prev => [...prev, extendedMessage]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Add error message
      const errorMessage: ExtendedChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, createSession]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
  }, []);

  return {
    messages,
    sendMessage,
    isLoading,
    clearMessages,
    sessionId
  };
};
