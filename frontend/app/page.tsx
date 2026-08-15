'use client';

import React, { useState, useEffect } from 'react';
import { Document, ChatMessage, Citation } from '../lib/types';
import {
  fetchDocuments,
  fetchDocumentStatus,
  uploadDocumentFile,
  deleteDocumentRecord,
  fetchDocumentMarkdown,
  fetchChatHistory
} from '../lib/api';

import DocumentSidebar from '../components/DocumentSidebar';
import DocumentHeader from '../components/DocumentHeader';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import CitationCard from '../components/CitationCard';
import DocumentViewer from '../components/DocumentViewer';

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isMdModalOpen, setIsMdModalOpen] = useState(false);
  const [markdownContent, setMarkdownContent] = useState('');

  const activeDoc = documents.find((d) => d.doc_id === activeDocId) || null;

  // Load documents list on mount
  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      if (docs.length > 0 && !activeDocId) {
        setActiveDocId(docs[0].doc_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Poll status if any document in the list is still processing/indexing/chunking
  useEffect(() => {
    const hasPendingDocs = documents.some(
      (d) => d.status !== 'ready' && d.status !== 'failed'
    );
    if (!hasPendingDocs) return;

    const interval = setInterval(async () => {
      try {
        const updatedDocs = await fetchDocuments();
        setDocuments(updatedDocs);
        const stillPending = updatedDocs.some(
          (d) => d.status !== 'ready' && d.status !== 'failed'
        );
        if (!stillPending) {
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Document status polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  // Load chat history when active document changes
  useEffect(() => {
    if (!activeDocId) {
      setMessages([]);
      return;
    }
    fetchChatHistory(activeDocId)
      .then((data) => {
        const turns: ChatMessage[] = [];
        data.history.forEach((h, idx) => {
          turns.push({ id: `q-${idx}`, sender: 'user', text: h.question });
          turns.push({ id: `a-${idx}`, sender: 'assistant', text: h.answer });
        });
        setMessages(turns);
      })
      .catch(() => setMessages([]));
  }, [activeDocId]);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const res = await uploadDocumentFile(file);
      await loadDocs();
      if (res.documents && res.documents.length > 0) {
        setActiveDocId(res.documents[0].doc_id);
      }
    } catch (err: any) {
      alert(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    if (activeDocId === docId) {
      const remaining = documents.filter((d) => d.doc_id !== docId);
      setActiveDocId(remaining.length > 0 ? remaining[0].doc_id : null);
    }
    try {
      await deleteDocumentRecord(docId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpenMarkdown = async () => {
    if (!activeDocId) return;
    try {
      const md = await fetchDocumentMarkdown(activeDocId);
      setMarkdownContent(md);
      setIsMdModalOpen(true);
    } catch (err: any) {
      alert('Markdown not available yet.');
    }
  };

  const handleSendQuestion = async (questionText: string) => {
    if (!activeDocId) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: questionText,
    };

    const assistantMsg: ChatMessage = {
      id: `asst-${Date.now()}`,
      sender: 'assistant',
      text: '',
      citations: [],
      streaming: true,
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
        throw new Error('Streaming failed');
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
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsg.id
                      ? { ...msg, citations: event.citations }
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
              }
            } catch (e) {
              console.error(e);
            }
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsg.id
            ? { ...msg, text: `Error: ${err.message}` }
            : msg
        )
      );
    }
  };

  return (
    <div className="app-container">
      <DocumentSidebar
        documents={documents}
        activeDocId={activeDocId}
        onSelectDoc={(id) => setActiveDocId(id)}
        onDeleteDoc={handleDelete}
        onUpload={handleUpload}
        isUploading={isUploading}
      />

      <main className="main-workspace">
        <DocumentHeader
          activeDoc={activeDoc}
          onOpenMarkdown={handleOpenMarkdown}
        />

        <ChatWindow
          messages={messages}
          activeDocReady={activeDoc?.status === 'ready'}
          onSampleClick={handleSendQuestion}
          onCitationClick={(cit) => setSelectedCitation(cit)}
        />

        <ChatInput
          disabled={!activeDoc || activeDoc.status !== 'ready'}
          onSend={handleSendQuestion}
        />
      </main>

      <CitationCard
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />

      <DocumentViewer
        isOpen={isMdModalOpen}
        filename={activeDoc?.filename || 'Document'}
        markdownContent={markdownContent}
        onClose={() => setIsMdModalOpen(false)}
      />
    </div>
  );
}
