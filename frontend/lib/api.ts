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
