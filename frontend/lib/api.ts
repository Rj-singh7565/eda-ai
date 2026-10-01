import { Document, UploadResponse, ChatMessage, SystemHealth } from './types';

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error('Failed to fetch system health');
  return res.json();
}

export async function fetchDashboardStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/stats`);
  if (!res.ok) throw new Error('Failed to fetch dashboard stats');
  return res.json();
}

export async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentStatus(docId: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}/status`);
  if (!res.ok) throw new Error('Failed to fetch document status');
  return res.json();
}

export async function uploadDocumentFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.message || 'Upload failed');
  }

  return res.json();
}

export async function deleteDocumentRecord(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function fetchDocumentMarkdown(docId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/documents/${docId}/markdown`);
  if (!res.ok) throw new Error('Failed to fetch document markdown');
  return res.text();
}

export async function fetchChatHistory(docId: string): Promise<{ history: { question: string; answer: string }[] }> {
  const res = await fetch(`${API_BASE}/api/chat/${docId}/history`);
  if (!res.ok) throw new Error('Failed to fetch chat history');
  return res.json();
}

export async function clearChatHistory(docId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/chat/${docId}/history`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const fallback = await fetch(`${API_BASE}/documents/${docId}/history`, { method: 'DELETE' });
    if (!fallback.ok) throw new Error('Failed to clear chat history');
    return fallback.json();
  }
  return res.json();
}

export interface SSEEventHandlers {
  onTableReady?: (data: {
    table_markdown: string;
    sql_query?: string;
    latency_ms?: number;
    row_count?: number;
    column_count?: number;
  }) => void;
  onMetadata?: (data: { citations: any[]; has_context: boolean }) => void;
  onCitation?: (data: { citations: any[] }) => void;
  onToken?: (token: string) => void;
  onError?: (errorMsg: string) => void;
  onDone?: (data: { status: string; total_latency_ms?: number }) => void;
}

export async function streamChatQuery(
  docId: string,
  question: string,
  handlers: SSEEventHandlers,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: docId, question }),
    signal
  });

  if (!response.ok) {
    let errorDetail = 'Streaming connection failed.';
    try {
      const errData = await response.json();
      if (errData && (errData.detail || errData.message)) {
        errorDetail = errData.detail || errData.message;
      }
    } catch (_) {}
    throw new Error(errorDetail);
  }

  if (!response.body) {
    throw new Error('Streaming response body is missing.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventType = 'message';
        let dataPayload = '';

        const lines = block.split(/\r?\n/);
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataPayload += (dataPayload ? '\n' : '') + line.slice(5).trim();
          }
        }

        if (!dataPayload) continue;

        try {
          const parsed = JSON.parse(dataPayload);
          const effectiveType = parsed.type || eventType;

          if (effectiveType === 'table_ready') {
            handlers.onTableReady?.(parsed);
          } else if (effectiveType === 'metadata') {
            handlers.onMetadata?.(parsed);
          } else if (effectiveType === 'citation') {
            handlers.onCitation?.(parsed);
          } else if (effectiveType === 'token') {
            handlers.onToken?.(parsed.content ?? parsed.token ?? '');
          } else if (effectiveType === 'done') {
            handlers.onDone?.(parsed);
          } else if (effectiveType === 'error') {
            handlers.onError?.(parsed.message || 'Error occurred');
          }
        } catch (e) {
          console.warn('SSE JSON parse note:', e, dataPayload);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

