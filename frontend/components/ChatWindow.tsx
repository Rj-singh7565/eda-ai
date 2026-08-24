'use client';

import React from 'react';
import { ChatMessage as ChatMessageType, Citation } from '../lib/types';
import ChatMessage from './ChatMessage';

interface ChatWindowProps {
  messages: ChatMessageType[];
  activeDocReady: boolean;
  onSampleClick: (query: string) => void;
  onCitationClick: (citationId: string) => void;
  onClearChat?: () => void;
}

export default function ChatWindow({
  messages,
  activeDocReady,
  onSampleClick,
  onCitationClick,
  onClearChat
}: ChatWindowProps) {
  return (
    <div className="col-chat">
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>AI Assistant</span>
          <span style={{ fontSize: '0.85rem' }}>🪄</span>
        </div>
        <button className="new-chat-btn" onClick={onClearChat} title="Clear conversation history">
          ⎘ New chat
        </button>
      </div>

      {/* Feed */}
      <div className="chat-feed">
        {messages.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', margin: 'auto 0', padding: '24px', textAlign: 'center', color: 'var(--muted)' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>💬</div>
            <div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '0.95rem', marginBottom: '4px' }}>
              Ask your Assistant
            </div>
            <div style={{ fontSize: '0.8rem', maxWidth: '280px' }}>
              Upload or select a document to ask natural language questions with precise page citations.
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onCitationClick={(cit: Citation) => onCitationClick(cit.id)}
            />
          ))
        )}

        {/* Suggested Prompts */}
        <div className="prompt-suggestions" style={{ marginTop: 'auto', paddingTop: '16px' }}>
          {[
            'Show placement stats by branch',
            'Show financial summary',
            'How many students graduated?'
          ].map((prompt, idx) => (
            <button
              key={idx}
              className="suggestion-chip"
              onClick={() => onSampleClick(prompt)}
            >
              &rarr; {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
