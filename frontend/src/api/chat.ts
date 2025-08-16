import { api } from './client';

export interface ChatSession {
  id: string;
  name?: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export async function createChatSession(name?: string): Promise<{ session_id: string }> {
  const res = await api.post('/chat/sessions', null, {
    params: { name }
  });
  return res.data;
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const res = await api.get('/chat/sessions');
  return res.data;
}

export async function sendMessage(sessionId: string, content: string, provider?: string): Promise<{ messages: ChatMessage[], sources?: any[] }> {
  const params: any = { content };
  if (provider) {
    params.provider = provider;
  }
  
  const res = await api.post(`/chat/sessions/${sessionId}/messages`, null, {
    params
  });
  return res.data;
}

export async function getChatMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await api.get(`/chat/sessions/${sessionId}/messages`);
  return res.data;
}
