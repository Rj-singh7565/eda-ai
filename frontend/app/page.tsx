'use client';

import React, { useState, useEffect } from 'react';
import { Document, ChatMessage, Citation, DashboardStats, SystemHealth, NavTab } from '../lib/types';
import {
  fetchDocuments,
  fetchDashboardStats,
  fetchSystemHealth,
  uploadDocumentFile,
  deleteDocumentRecord,
  fetchDocumentMarkdown,
  fetchChatHistory,
  API_BASE
} from '../lib/api';

import NavSidebar from '../components/NavSidebar';
import GlobalHeader from '../components/GlobalHeader';
import OverviewDashboard from '../components/dashboard/OverviewDashboard';
import DatasetsView from '../components/dashboard/DatasetsView';
import HistoryView from '../components/dashboard/HistoryView';
import StorageView from '../components/dashboard/StorageView';
import SettingsView from '../components/dashboard/SettingsView';
import AnalysisWorkspace from '../components/analysis/AnalysisWorkspace';

import SourceViewer from '../components/SourceViewer';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import CitationsPanel from '../components/CitationsPanel';
import DocumentViewer from '../components/DocumentViewer';
import ExportModal from '../components/ExportModal';

export default function DashboardPage() {
  const [activeNavTab, setActiveNavTab] = useState<NavTab>('overview');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Analysis Workspace state
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'chat' | 'source'>('chat');
  const [isCitationsDrawerOpen, setIsCitationsDrawerOpen] = useState(false);
  const [activeCoordinate, setActiveCoordinate] = useState('1');
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [markdownContent, setMarkdownContent] = useState('');
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  // Preview Modal state
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);
  const [previewMarkdown, setPreviewMarkdown] = useState<string>('');

  const activeDoc = documents.find((d) => d.doc_id === activeDocId) || (documents.length > 0 ? documents[0] : null);

  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    setToast({ type, message });
    setTimeout(() => {
      setToast((current) => (current?.message === message ? null : current));
    }, 5000);
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [backendDocs, dashboardStats, systemHealth] = await Promise.all([
        fetchDocuments().catch(() => []),
        fetchDashboardStats().catch(() => null),
        fetchSystemHealth().catch(() => null)
      ]);

      if (Array.isArray(backendDocs)) {
        setDocuments(backendDocs);
        if (backendDocs.length > 0) {
          setActiveDocId((prev) => (prev && backendDocs.some((d) => d.doc_id === prev) ? prev : backendDocs[0].doc_id));
        }
      }

      if (dashboardStats) setStats(dashboardStats);
      if (systemHealth) setHealth(systemHealth);
    } catch (err: any) {
      console.error('Initial data load note:', err);
    }
  };

  useEffect(() => {
    if (!activeDocId) {
      setMarkdownContent('');
      setMessages([]);
      return;
    }

    fetchDocumentMarkdown(activeDocId)
      .then((md) => setMarkdownContent(md))
      .catch(() => setMarkdownContent(''));

    fetchChatHistory(activeDocId)
      .then((res) => {
        if (res && Array.isArray(res.history)) {
          const restoredMessages: ChatMessage[] = [];
          res.history.forEach((turn, idx) => {
            restoredMessages.push({
              id: `hist-user-${idx}`,
              sender: 'user',
              text: turn.question,
              timestamp: 'Previous session'
            });
            restoredMessages.push({
              id: `hist-asst-${idx}`,
              sender: 'assistant',
              text: turn.answer,
              timestamp: 'Previous session'
            });
          });
          setMessages(restoredMessages);
        }
      })
      .catch(() => {});
  }, [activeDocId]);

  // Polling loop for processing documents
  useEffect(() => {
    const processingDocs = documents.filter((d) =>
      ['processing', 'parsing', 'normalizing', 'chunking', 'embedding', 'indexing'].includes(d.status)
    );

    if (processingDocs.length === 0) return;

    const interval = setInterval(async () => {
      try {
        const updatedDocs = await fetchDocuments();
        if (Array.isArray(updatedDocs)) {
          setDocuments(updatedDocs);
        }
        const updatedStats = await fetchDashboardStats();
        if (updatedStats) setStats(updatedStats);
      } catch (e) {
        console.error('Polling status note:', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const res = await uploadDocumentFile(file);

      const newDocs: Document[] = [];
      if (res.documents && Array.isArray(res.documents) && res.documents.length > 0) {
        newDocs.push(...res.documents);
      } else if (res.doc_id) {
        newDocs.push({
          doc_id: res.doc_id,
          filename: res.filename || file.name,
          file_size: file.size,
          file_type: res.file_type || 'pdf',
          status: 'processing'
        });
      }

      if (newDocs.length > 0) {
        setDocuments((prev) => {
          const existingIds = new Set(prev.map((d) => d.doc_id));
          const additions = newDocs.filter((d) => !existingIds.has(d.doc_id));
          return [...additions, ...prev];
        });
        setActiveDocId(newDocs[0].doc_id);
      }

      showToast('success', res.message || `Uploaded ${file.name} successfully. Ingestion initiated.`);

      const [updatedDocs, updatedStats] = await Promise.all([
        fetchDocuments().catch(() => []),
        fetchDashboardStats().catch(() => null)
      ]);

      if (Array.isArray(updatedDocs)) setDocuments(updatedDocs);
      if (updatedStats) setStats(updatedStats);
    } catch (err: any) {
      console.error('Upload error:', err);
      showToast('error', err.message || 'File upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    setDocuments((prev) => {
      const nextDocs = prev.filter((d) => d.doc_id !== docId);
      if (activeDocId === docId) {
        setActiveDocId(nextDocs.length > 0 ? nextDocs[0].doc_id : null);
      }
      return nextDocs;
    });

    try {
      await deleteDocumentRecord(docId);
      const [backendDocs, updatedStats] = await Promise.all([
        fetchDocuments().catch(() => []),
        fetchDashboardStats().catch(() => null)
      ]);

      if (Array.isArray(backendDocs)) {
        setDocuments(backendDocs);
        if (backendDocs.length === 0) {
          setActiveDocId(null);
        }
      }
      if (updatedStats) setStats(updatedStats);
      showToast('info', 'Dataset deleted successfully.');
    } catch (err: any) {
      console.error('Deletion error:', err);
      showToast('error', 'Failed to delete dataset.');
    }
  };

  const handlePreview = async (doc: Document) => {
    setPreviewDoc(doc);
    try {
      const md = await fetchDocumentMarkdown(doc.doc_id);
      setPreviewMarkdown(md);
    } catch (e) {
      setPreviewMarkdown('# Document Preview\n\nMarkdown representation is loading or processing.');
    }
  };

  const handleSendQuestion = async (questionText: string) => {
    if (!activeDocId || !activeDoc || activeDoc.status !== 'ready') return;

    const startTime = Date.now();

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: questionText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const assistantMsg: ChatMessage = {
      id: `asst-${Date.now()}`,
      sender: 'assistant',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      streaming: true,
      latencyMs: 0
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: activeDocId, question: questionText })
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

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;
            try {
              const event = JSON.parse(dataStr);
              if (event.type === 'metadata') {
                const mappedCitations: Citation[] = (event.citations || []).map((c: any, idx: number) => ({
                  id: `cit-${Date.now()}-${idx}`,
                  doc_id: activeDocId,
                  document_name: activeDoc?.filename || 'Document',
                  category: c.is_table ? 'table' : 'text',
                  location: c.pages && c.pages.length > 0 ? `Page ${c.pages.join(', ')}` : 'Excerpt',
                  snippet: c.text_snippet || c.full_text || '',
                  match_type: c.score > 0.85 ? 'Exact match' : 'Text match',
                  score: c.score || 0.8,
                  pages: c.pages || []
                }));
                setActiveCitations(mappedCitations);
                if (mappedCitations.length > 0) {
                  setIsCitationsDrawerOpen(true);
                }
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id ? { ...msg, citations: mappedCitations } : msg
                  )
                );
              } else if (event.type === 'token') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id ? { ...msg, text: msg.text + event.content } : msg
                  )
                );
              } else if (event.type === 'done') {
                const elapsed = Date.now() - startTime;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id ? { ...msg, streaming: false, latencyMs: elapsed } : msg
                  )
                );
                // Refresh stats after Q&A completes
                fetchDashboardStats().then((s) => s && setStats(s)).catch(() => {});
              } else if (event.type === 'error') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id
                      ? { ...msg, text: event.message || 'Error generating answer.', streaming: false }
                      : msg
                  )
                );
              }
            } catch (e) {
              console.error('Error parsing SSE event:', e);
            }
          }
        }
      }
    } catch (err: any) {
      const isFetchErr = err.message && err.message.includes('Failed to fetch');
      const errDisplay = isFetchErr
        ? `Could not connect to FastAPI backend server (${API_BASE}). Please verify backend service is running.`
        : `Error: ${err.message || 'Failed to connect to assistant backend.'}`;

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsg.id ? { ...msg, text: errDisplay, streaming: false } : msg
        )
      );
    }
  };

  // Export Modal state
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

  const handleExportReport = () => {
    if (!messages.length) {
      showToast('info', 'No analysis queries yet. Ask a question or run a query before exporting.');
      setIsExportModalOpen(true);
      return;
    }
    setIsExportModalOpen(true);
  };

  return (
    <div className="app-viewport">
      {/* Toast Notification */}
      {toast && (
        <div
          style={{
            position: 'fixed',
            top: '16px',
            right: '20px',
            zIndex: 9999,
            padding: '12px 18px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.84rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
            backgroundColor:
              toast.type === 'error'
                ? '#FEE2E2'
                : toast.type === 'success'
                ? '#D1FAE5'
                : '#E0E7FF',
            color:
              toast.type === 'error'
                ? '#991B1B'
                : toast.type === 'success'
                ? '#065F46'
                : '#3730A3',
            border: `1px solid ${
              toast.type === 'error'
                ? '#FCA5A5'
                : toast.type === 'success'
                ? '#6EE7B7'
                : '#A5B4FC'
            }`,
            transition: 'all 0.3s ease'
          }}
        >
          <span>{toast.type === 'error' ? '⚠️' : toast.type === 'success' ? '✅' : 'ℹ️'}</span>
          <span>{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.9rem',
              color: 'inherit',
              marginLeft: '8px'
            }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Preview Modal */}
      {previewDoc && (
        <DocumentViewer
          isOpen={true}
          filename={previewDoc.filename}
          markdownContent={previewMarkdown}
          onClose={() => setPreviewDoc(null)}
        />
      )}

      {/* Multi-Format Export Modal (PDF, Excel, CSV, JSON, Markdown) */}
      <ExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        activeDoc={activeDoc}
        messages={messages}
        onShowToast={showToast}
      />

      {/* Left Navigation Rail (~260px) */}
      <NavSidebar
        activeTab={activeNavTab}
        onTabChange={setActiveNavTab}
        activeDoc={activeDoc}
        onPreviewDoc={handlePreview}
      />

      {/* Main Workspace */}
      <div className="main-workspace-wrapper">
        {/* Top Global Header */}
        <GlobalHeader
          activeTab={activeNavTab}
          activeDoc={activeDoc}
          documents={documents}
          onSelectDoc={(id) => setActiveDocId(id)}
          onExportReport={handleExportReport}
        />

        {/* Dynamic Tab Body */}
        <div className="workspace-tab-viewport">
          {activeNavTab === 'overview' && (
            <OverviewDashboard
              stats={stats}
              documents={documents}
              activeDoc={activeDoc}
              onSelectDoc={(id) => setActiveDocId(id)}
              onPreviewDoc={handlePreview}
              onDeleteDoc={handleDelete}
              onStartAnalysis={(id) => {
                setActiveDocId(id);
                setActiveNavTab('analysis');
              }}
              onUpload={handleUpload}
              isUploading={isUploading}
              onNavigateTab={setActiveNavTab}
            />
          )}

          {activeNavTab === 'datasets' && (
            <DatasetsView
              documents={documents}
              activeDocId={activeDocId}
              onSelectDoc={(id) => setActiveDocId(id)}
              onPreviewDoc={handlePreview}
              onDeleteDoc={handleDelete}
              onStartAnalysis={(id) => {
                setActiveDocId(id);
                setActiveNavTab('analysis');
              }}
              onUpload={handleUpload}
              isUploading={isUploading}
            />
          )}

          {activeNavTab === 'analysis' && (
            <AnalysisWorkspace
              documents={documents}
              activeDoc={activeDoc}
              onSelectDoc={(id) => setActiveDocId(id)}
              messages={messages}
              onSendMessage={handleSendQuestion}
              onClearChat={() => setMessages([])}
              onExportPDF={handleExportReport}
              health={health}
              isStreaming={messages.some((m) => m.streaming)}
            />
          )}

          {activeNavTab === 'history' && (
            <HistoryView
              documents={documents}
              activeDoc={activeDoc}
              messages={messages}
              onSelectDoc={(id) => setActiveDocId(id)}
              onOpenAnalysis={() => setActiveNavTab('analysis')}
            />
          )}

          {activeNavTab === 'storage' && (
            <StorageView documents={documents} stats={stats} health={health} />
          )}

          {activeNavTab === 'settings' && <SettingsView health={health} />}
        </div>
      </div>
    </div>
  );
}
