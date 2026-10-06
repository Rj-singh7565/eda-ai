'use client';

import React, { useState, useEffect, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Document, ChatMessage, Citation, DashboardStats, SystemHealth, NavTab } from '../lib/types';
import {
  fetchDocuments,
  fetchDashboardStats,
  uploadDocumentFile,
  deleteDocumentRecord,
  fetchDocumentMarkdown,
  fetchChatHistory,
  clearChatHistory,
  streamChatQuery,
  API_BASE
} from '../lib/api';

import dynamic from 'next/dynamic';
import NavSidebar from './NavSidebar';
import GlobalHeader from './GlobalHeader';
import OverviewDashboard from './dashboard/OverviewDashboard';

// Dynamically loaded views and modals — deferred until user selects their respective tab
const DatasetsView = dynamic(() => import('./dashboard/DatasetsView'));
const HistoryView = dynamic(() => import('./dashboard/HistoryView'));
const StorageView = dynamic(() => import('./dashboard/StorageView'));
const SettingsView = dynamic(() => import('./dashboard/SettingsView'));
const AnalysisWorkspace = dynamic(() => import('./analysis/AnalysisWorkspace'));

const DocumentViewer = dynamic(() => import('./DocumentViewer'), { ssr: false });
const ExportModal = dynamic(() => import('./ExportModal'), { ssr: false });

interface DashboardClientContainerProps {
  initialDocuments: Document[];
  initialStats: DashboardStats | null;
  initialHealth: SystemHealth | null;
  initialHistory?: { question: string; answer: string }[];
}

export default function DashboardClientContainer({
  initialDocuments,
  initialStats,
  initialHealth,
  initialHistory = []
}: DashboardClientContainerProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const [activeNavTab, setActiveNavTab] = useState<NavTab>('overview');
  const [documents, setDocuments] = useState<Document[]>(initialDocuments);
  const [activeDocId, setActiveDocId] = useState<string | null>(
    initialDocuments.length > 0 ? initialDocuments[0].doc_id : null
  );
  const [stats, setStats] = useState<DashboardStats | null>(initialStats);
  const [health, setHealth] = useState<SystemHealth | null>(initialHealth);
  const [isUploading, setIsUploading] = useState(false);

  // Parse initial history into ChatMessages
  const initialMessages: ChatMessage[] = React.useMemo(() => {
    if (!initialHistory || !Array.isArray(initialHistory) || initialHistory.length === 0) {
      return [];
    }
    const msgs: ChatMessage[] = [];
    initialHistory.forEach((turn, idx) => {
      msgs.push({
        id: `hist-user-${idx}`,
        sender: 'user',
        text: turn.question,
        timestamp: 'Previous session'
      });
      msgs.push({
        id: `hist-asst-${idx}`,
        sender: 'assistant',
        text: turn.answer,
        timestamp: 'Previous session'
      });
    });
    return msgs;
  }, [initialHistory]);

  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [markdownContent, setMarkdownContent] = useState('');
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [isCitationsDrawerOpen, setIsCitationsDrawerOpen] = useState(false);

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

  // Sync state if server revalidates props
  useEffect(() => {
    if (initialDocuments && initialDocuments.length > 0) {
      setDocuments(initialDocuments);
      if (!activeDocId) {
        setActiveDocId(initialDocuments[0].doc_id);
      }
    }
  }, [initialDocuments]);

  useEffect(() => {
    if (initialStats) setStats(initialStats);
  }, [initialStats]);

  useEffect(() => {
    if (initialHealth) setHealth(initialHealth);
  }, [initialHealth]);

  // Load document-specific history only when user switches active document away from initial
  const isFirstRender = React.useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return; // Skip first render because initial history was already provided by SSR
    }

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

  // Polling loop ONLY for active in-flight processing documents
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

      // Trigger background SSR cache revalidation
      startTransition(() => {
        router.refresh();
      });

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
      // Trigger background SSR cache revalidation
      startTransition(() => {
        router.refresh();
      });

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
      await streamChatQuery(activeDocId, questionText, {
        onTableReady: (tableData) => {
          const elapsed = Date.now() - startTime;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsg.id
                ? {
                    ...msg,
                    text: tableData.table_markdown,
                    tableMarkdown: tableData.table_markdown,
                    sqlQuery: tableData.sql_query,
                    latencyMs: tableData.latency_ms || elapsed
                  }
                : msg
            )
          );
        },
        onMetadata: (event) => {
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
        },
        onToken: (tok) => {
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMsg.id) return msg;
              if (msg.tableMarkdown && tok.startsWith('|') && msg.text.includes(tok.slice(0, 30))) {
                return msg;
              }
              return { ...msg, text: msg.text + tok };
            })
          );
        },
        onDone: (data) => {
          const elapsed = Date.now() - startTime;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsg.id
                ? { ...msg, streaming: false, latencyMs: data.total_latency_ms || elapsed }
                : msg
            )
          );
          fetchDashboardStats().then((s) => s && setStats(s)).catch(() => {});
        },
        onError: (errMsg) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsg.id ? { ...msg, text: errMsg, streaming: false } : msg
            )
          );
        }
      });
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

  const handleClearChat = async () => {
    setMessages([]);
    if (activeDocId) {
      try {
        await clearChatHistory(activeDocId);
      } catch (err) {
        console.warn('Backend clear history note:', err);
      }
    }
    showToast('info', 'Chat history cleared.');
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

      {/* Multi-Format Export Modal */}
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
              onClearChat={handleClearChat}
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
