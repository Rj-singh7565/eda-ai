'use client';

import React from 'react';
import { Clock, MessageSquare, Sparkles, FileText, ArrowRight } from 'lucide-react';
import { Document, ChatMessage } from '../../lib/types';

interface HistoryViewProps {
  documents: Document[];
  activeDoc: Document | null;
  messages: ChatMessage[];
  onSelectDoc: (docId: string) => void;
  onOpenAnalysis: () => void;
}

export default function HistoryView({
  documents,
  activeDoc,
  messages,
  onSelectDoc,
  onOpenAnalysis
}: HistoryViewProps) {
  return (
    <div className="history-view-container">
      <div className="dashboard-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Conversation & Analysis History</h2>
            <span className="panel-subtitle">
              Past Q&A turns for active dataset:{' '}
              <strong>{activeDoc ? activeDoc.filename : 'None selected'}</strong>
            </span>
          </div>
          <button className="panel-view-all-btn" onClick={onOpenAnalysis}>
            Open Live Workspace <ArrowRight size={14} style={{ display: 'inline', marginLeft: '4px' }} />
          </button>
        </div>

        <div className="history-feed-scrollable">
          {messages.length === 0 ? (
            <div className="history-empty-state">
              <div className="history-empty-icon-box">
                <Clock size={32} />
              </div>
              <h3 className="history-empty-title">No analysis history yet</h3>
              <p className="history-empty-text">
                Ask questions about {activeDoc ? activeDoc.filename : 'your datasets'} in the Analysis workspace to build verifiable conversational history.
              </p>
              <button className="view-primary-action-btn" onClick={onOpenAnalysis} style={{ margin: '16px auto 0' }}>
                <Sparkles size={16} />
                <span>Start New Analysis</span>
              </button>
            </div>
          ) : (
            <div className="history-thread-list">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`history-card-bubble ${msg.sender === 'user' ? 'user' : 'assistant'}`}
                >
                  <div className="history-bubble-header">
                    <span className="history-bubble-sender">
                      {msg.sender === 'user' ? '👤 User Prompt' : '✨ EDA Assistant Response'}
                    </span>
                    <span className="history-bubble-time">{msg.timestamp || 'Recent'}</span>
                  </div>
                  <div className="history-bubble-body">{msg.text}</div>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="history-bubble-citations">
                      <span className="citations-label">Grounded Evidence:</span>
                      {msg.citations.map((c, cIdx) => (
                        <span key={cIdx} className="history-citation-chip">
                          📍 {c.location}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
