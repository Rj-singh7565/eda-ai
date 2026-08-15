'use client';

import React from 'react';
import { ChatMessage as ChatMessageType, Citation } from '../lib/types';
import ChatMessage from './ChatMessage';

interface ChatWindowProps {
  messages: ChatMessageType[];
  activeDocReady: boolean;
  onSampleClick: (query: string) => void;
  onCitationClick: (citation: Citation) => void;
}

export default function ChatWindow({
  messages,
  activeDocReady,
  onSampleClick,
  onCitationClick
}: ChatWindowProps) {
  if (!activeDocReady && messages.length === 0) {
    return (
      <div className="chat-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', maxWidth: '420px', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>📊</div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
            No Active Document Selected
          </h2>
          <p style={{ fontSize: '0.88rem', lineHeight: '1.5' }}>
            Upload a PDF, DOCX, PPTX, Excel, CSV, or ZIP file from the sidebar to start asking natural-language analytical questions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {messages.length === 0 && activeDocReady && (
        <div style={{ marginBottom: '20px' }}>
          <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Suggested Analytical Queries
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {[
              'Summarize key financial highlights and major revenue metrics.',
              'What are the primary operational risks and key challenges mentioned?',
              'Provide a breakdown of top performing departments and key KPIs.',
              'Synthesize the executive summary and strategic recommendations.'
            ].map((q, idx) => (
              <button
                key={idx}
                onClick={() => onSampleClick(q)}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  padding: '8px 14px',
                  borderRadius: '20px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast)'
                }}
              >
                💡 {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-messages">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} onCitationClick={onCitationClick} />
        ))}
      </div>
    </div>
  );
}
