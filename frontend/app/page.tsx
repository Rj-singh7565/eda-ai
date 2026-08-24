'use client';

import React, { useState, useEffect } from 'react';
import { Document, ChatMessage, Citation } from '../lib/types';
import {
  fetchDocuments,
  uploadDocumentFile,
  deleteDocumentRecord,
  fetchDocumentMarkdown,
  fetchChatHistory
} from '../lib/api';

import NavSidebar from '../components/NavSidebar';
import DocumentSidebar from '../components/DocumentSidebar';
import SourceViewer from '../components/SourceViewer';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import CitationsPanel from '../components/CitationsPanel';

export default function DashboardPage() {
  const [activeNavTab, setActiveNavTab] = useState('documents');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [sidebarSearch, setSidebarSearch] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'chat' | 'source'>('chat');
  const [isCitationsDrawerOpen, setIsCitationsDrawerOpen] = useState(false);

  const [activeCoordinate, setActiveCoordinate] = useState('1');
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [markdownContent, setMarkdownContent] = useState('');
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  const activeDoc = documents.find((d) => d.doc_id === activeDocId) || null;

  useEffect(() => {
    loadDocs();
  }, []);

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
      } catch (e) {
        console.error('Polling status error:', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  const loadDocs = async () => {
    try {
      const backendDocs = await fetchDocuments();
      if (Array.isArray(backendDocs)) {
        setDocuments(backendDocs);
        if (backendDocs.length > 0) {
          setActiveDocId((prev) => (prev && backendDocs.some(d => d.doc_id === prev) ? prev : backendDocs[0].doc_id));
        } else {
          setActiveDocId(null);
        }
      }
    } catch (err) {
      setDocuments([]);
      setActiveDocId(null);
    }
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const res = await uploadDocumentFile(file);
      const updatedDocs = await fetchDocuments();
      setDocuments(updatedDocs);
      if (res.documents && res.documents.length > 0) {
        setActiveDocId(res.documents[0].doc_id);
      }
    } catch (err: any) {
      const newDoc: Document = {
        doc_id: `upload-${Date.now()}`,
        filename: file.name,
        file_size: file.size,
        file_type: file.name.split('.').pop()?.toUpperCase() || 'FILE',
        status: 'ready'
      };
      setDocuments((prev) => [newDoc, ...prev]);
      setActiveDocId(newDoc.doc_id);
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
      const backendDocs = await fetchDocuments();
      if (Array.isArray(backendDocs)) {
        setDocuments(backendDocs);
        if (backendDocs.length === 0) {
          setActiveDocId(null);
        }
      }
    } catch (err) {
      console.error('Deletion error:', err);
    }
  };

  const handleSendQuestion = async (questionText: string) => {
    if (!activeDocId) return;

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
      streaming: true
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const response = await fetch(`${apiBase}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: activeDocId, question: questionText }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Streaming connection failed');
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
                    msg.id === assistantMsg.id
                      ? { ...msg, citations: mappedCitations }
                      : msg
                  )
                );
              } else if (event.type === 'token') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id
                      ? { ...msg, text: msg.text + event.content }
                      : msg
                  )
                );
              } else if (event.type === 'done') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id ? { ...msg, streaming: false } : msg
                  )
                );
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
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsg.id
            ? { ...msg, text: `Error: ${err.message || 'Failed to connect to assistant backend.'}`, streaming: false }
            : msg
        )
      );
    }
  };

  const handleSelectCoordinate = (coord: string) => {
    setActiveCoordinate(coord);
  };

  const handleSelectCitation = (citationId: string) => {
    setSelectedCitationId(citationId);
    setIsCitationsDrawerOpen(true);
  };

  return (
    <div className="app-viewport">
      <NavSidebar
        activeTab={activeNavTab}
        onTabChange={setActiveNavTab}
      />

      <DocumentSidebar
        documents={documents}
        activeDocId={activeDocId}
        onSelectDoc={(id) => setActiveDocId(id)}
        onDeleteDoc={handleDelete}
        onUpload={handleUpload}
        isUploading={isUploading}
        searchFilter={sidebarSearch}
        onSearchFilterChange={setSidebarSearch}
      />

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', backgroundColor: 'var(--surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px', backgroundColor: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveWorkspaceTab('chat')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '0.84rem',
                fontWeight: 600,
                border: '1px solid',
                cursor: 'pointer',
                borderColor: activeWorkspaceTab === 'chat' ? 'var(--slate)' : 'var(--border)',
                backgroundColor: activeWorkspaceTab === 'chat' ? 'var(--slate-soft)' : 'var(--paper)',
                color: activeWorkspaceTab === 'chat' ? 'var(--slate)' : 'var(--ink)'
              }}
            >
              💬 AI Assistant
            </button>
            <button
              onClick={() => setActiveWorkspaceTab('source')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '0.84rem',
                fontWeight: 600,
                border: '1px solid',
                cursor: 'pointer',
                borderColor: activeWorkspaceTab === 'source' ? 'var(--slate)' : 'var(--border)',
                backgroundColor: activeWorkspaceTab === 'source' ? 'var(--slate-soft)' : 'var(--paper)',
                color: activeWorkspaceTab === 'source' ? 'var(--slate)' : 'var(--ink)'
              }}
            >
              📄 Document Viewer {activeDoc ? `(${activeDoc.filename})` : ''}
            </button>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {activeWorkspaceTab === 'chat' ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
              <ChatInput
                disabled={!activeDoc}
                onSend={handleSendQuestion}
              />
              <ChatWindow
                messages={messages}
                activeDocReady={activeDoc?.status === 'ready'}
                onSampleClick={handleSendQuestion}
                onCitationClick={handleSelectCitation}
                onClearChat={() => setMessages([])}
              />
            </div>
          ) : (
            <SourceViewer
              filename={activeDoc?.filename || ''}
              activeCoordinate={activeCoordinate}
              onSelectCoordinate={handleSelectCoordinate}
              markdownContent={markdownContent}
            />
          )}
        </div>
      </main>
    </div>
  );
}
