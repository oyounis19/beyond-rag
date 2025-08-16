import { api } from './client';

export interface Document {
  id: string;
  name: string;
  status: string;
  created_at: string;
  current_version_id?: string;
}

export interface DocumentStatus {
  document: {
    id: string;
    name: string;
    status: string;
    created_at: string;
    file_hash?: string;
    effective_at?: string;
  };
  total_chunks: number;
  total_conflicts: number;
  total_dedup_groups: number;
}

export interface ProcessingStatus {
  stage: 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'analyzing' | 'published' | 'pending_review' | 'error';
  message?: string;
  progress?: number;
}

export async function listDocuments(): Promise<Document[]> {
  const res = await api.get('/documents');
  return res.data;
}

export async function uploadDocument(file: File, title?: string): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  const res = await api.post('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
}

export async function publishDocument(documentId: string, docling: boolean = false): Promise<any> {
  // Use longer timeout for publish operations (2 minutes)
  const res = await api.post(`/documents/${documentId}/publish?docling=${docling}`, null, {
    timeout: 120000 // 2 minutes
  });
  return res.data;
}

export interface PublishEvent {
  stage: string;
  message?: string;
  progress?: number;
  ok?: boolean;
  error?: string;
  chunks_created?: number;
  chunks_embedded?: number;
  chunks_processed?: number;
  total_chunks?: number;
  estimated_time?: string;
  duplicates_count?: number;
  contradictions_count?: number;
  requires_review?: boolean;
  published?: boolean;
  document_id?: string;
}

export function publishDocumentStream(
  documentId: string, 
  docling: boolean = false,
  onEvent: (event: PublishEvent) => void,
  onError: (error: string) => void,
  onComplete: () => void
): () => void {
  const eventSource = new EventSource(
    `${api.defaults.baseURL}/documents/${documentId}/publish-stream?docling=${docling}`
  );

  eventSource.onmessage = (event) => {
    try {
      const data: PublishEvent = JSON.parse(event.data);
      onEvent(data);
      
      // Close connection on completion or error
      if (data.stage === 'complete' || data.stage === 'conflicts_detected' || data.stage === 'error') {
        eventSource.close();
        onComplete();
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err);
      onError('Failed to parse server response');
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    eventSource.close();
    onError('Connection to server lost');
    onComplete();
  };

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}

export async function publishDocumentAsync(documentId: string, docling: boolean = false): Promise<any> {
  // Start the publish process (fire and forget)
  try {
    const res = await api.post(`/documents/${documentId}/publish?docling=${docling}`, null, {
      timeout: 5000 // Short timeout for the initial request
    });
    return res.data;
  } catch (error: any) {
    // If it times out, that's expected for long operations
    if (error.code === 'ECONNABORTED' || error.code === 'TIMEOUT') {
      return { ok: true, processing: true, message: 'Document processing started' };
    }
    throw error;
  }
}

export async function pollDocumentStatus(documentId: string, maxPolls: number = 60, intervalMs: number = 2000): Promise<DocumentStatus> {
  for (let i = 0; i < maxPolls; i++) {
    const status = await getDocumentStatus(documentId);
    
    // Check if processing is complete
    if (status.document.status === 'published' || 
        status.document.status === 'pending_review' || 
        status.document.status === 'error') {
      return status;
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  
  throw new Error('Polling timeout: Document processing took too long');
}

export async function deleteDocument(documentId: string): Promise<any> {
  const res = await api.delete(`/documents/${documentId}`);
  return res.data;
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatus> {
  const res = await api.get(`/documents/${documentId}/status`);
  return res.data;
}
