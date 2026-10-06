import { Document, DashboardStats, SystemHealth } from '../types';

/**
 * Server-side Data Access Layer for Next.js Server Components.
 * Direct communication from Next.js server to FastAPI backend.
 * Never executes in the browser.
 */

const SERVER_API_BASE = (
  process.env.INTERNAL_API_URL ||
  process.env.FASTAPI_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://127.0.0.1:8000'
).replace(/\/+$/, '');

export async function getServerDocuments(): Promise<Document[]> {
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/documents`, {
      cache: 'no-store', // Always get fresh document catalog on request
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!res.ok) {
      console.warn(`[SSR API] getServerDocuments returned status ${res.status}`);
      return [];
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (error: any) {
    console.warn(`[SSR API] getServerDocuments connection note: ${error.message}`);
    return [];
  }
}

export async function getServerDashboardStats(): Promise<DashboardStats | null> {
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/stats`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!res.ok) {
      console.warn(`[SSR API] getServerDashboardStats returned status ${res.status}`);
      return null;
    }
    return await res.json();
  } catch (error: any) {
    console.warn(`[SSR API] getServerDashboardStats connection note: ${error.message}`);
    return null;
  }
}

export async function getServerSystemHealth(): Promise<SystemHealth | null> {
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/health`, {
      next: { revalidate: 30 }, // Safe to cache health for 30s
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!res.ok) {
      console.warn(`[SSR API] getServerSystemHealth returned status ${res.status}`);
      return null;
    }
    return await res.json();
  } catch (error: any) {
    console.warn(`[SSR API] getServerSystemHealth connection note: ${error.message}`);
    return null;
  }
}

export async function getServerDocumentMarkdown(docId: string): Promise<string> {
  if (!docId) return '';
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/documents/${encodeURIComponent(docId)}/markdown`, {
      next: { revalidate: 120 }, // Processed markdown is immutable per document ID
    });
    if (!res.ok) return '';
    return await res.text();
  } catch (error: any) {
    console.warn(`[SSR API] getServerDocumentMarkdown note: ${error.message}`);
    return '';
  }
}

export async function getServerChatHistory(docId: string): Promise<{ history: { question: string; answer: string }[] }> {
  if (!docId) return { history: [] };
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/chat/${encodeURIComponent(docId)}/history`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!res.ok) return { history: [] };
    const data = await res.json();
    return data && Array.isArray(data.history) ? data : { history: [] };
  } catch (error: any) {
    console.warn(`[SSR API] getServerChatHistory note: ${error.message}`);
    return { history: [] };
  }
}
