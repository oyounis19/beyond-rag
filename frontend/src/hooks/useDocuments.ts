import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDocuments, uploadDocument, publishDocument, getDocumentStatus, Document, DocumentStatus } from '../api/documents';

export function useDocuments() {
  return useQuery<Document[], Error>({
    queryKey: ['documents'],
    queryFn: () => listDocuments(),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) => uploadDocument(file, title),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function usePublishDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, docling }: { documentId: string; docling?: boolean }) => 
      publishDocument(documentId, docling),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useDocumentStatus(documentId: string) {
  return useQuery<DocumentStatus, Error>({
    queryKey: ['document-status', documentId],
    queryFn: () => getDocumentStatus(documentId),
    enabled: !!documentId,
    refetchInterval: (query) => {
      // Auto-refresh if document is still processing
      const status = query.state.data?.document?.status;
      return status === 'draft' ? 2000 : false;
    },
  });
}
