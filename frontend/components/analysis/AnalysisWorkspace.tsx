'use client';

import React from 'react';
import {
  Sparkles,
  Table as TableIcon,
  BarChart2,
  Users,
  Search,
  TrendingUp
} from 'lucide-react';
import { Document, ChatMessage, SystemHealth } from '../../lib/types';
import AnalysisTurnCard from './AnalysisTurnCard';
import CommandBar from './CommandBar';

interface AnalysisWorkspaceProps {
  documents: Document[];
  activeDoc: Document | null;
  onSelectDoc: (docId: string) => void;
  messages: ChatMessage[];
  onSendMessage: (query: string) => void;
  onClearChat: () => void;
  onExportPDF: () => void;
  health: SystemHealth | null;
  isStreaming?: boolean;
}

export default function AnalysisWorkspace({
  documents,
  activeDoc,
  onSelectDoc,
  messages,
  onSendMessage,
  onClearChat,
  onExportPDF,
  health,
  isStreaming = false
}: AnalysisWorkspaceProps) {
  // Group messages into paired turns
  const turns: {
    id: string;
    question: string;
    answer: string;
    timestamp?: string;
    streaming?: boolean;
    latencyMs?: number;
    tableMarkdown?: string;
    sqlQuery?: string;
    pythonQuery?: string;
    analyticalPlan?: any;
    datasetName?: string;
    datasetId?: string;
    datasetVersion?: string;
    queryId?: string;
    operations?: string[];
    library?: string;
  }[] = [];
  
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].sender === 'user') {
      const q = messages[i].text;
      const t = messages[i].timestamp;
      let a = '';
      let isStream = false;
      let latency = 0;
      let tableMarkdown = undefined;
      let sqlQuery = undefined;
      let pythonQuery = undefined;
      let analyticalPlan = undefined;
      let datasetName = undefined;
      let datasetId = undefined;
      let datasetVersion = undefined;
      let queryId = undefined;
      let operations = undefined;
      let library = undefined;

      if (i + 1 < messages.length && messages[i + 1].sender === 'assistant') {
        const asst = messages[i + 1];
        a = asst.text;
        isStream = !!asst.streaming;
        latency = asst.latencyMs || 0;
        tableMarkdown = asst.tableMarkdown;
        sqlQuery = asst.sqlQuery;
        pythonQuery = asst.pythonQuery;
        analyticalPlan = asst.analyticalPlan;
        datasetName = asst.datasetName;
        datasetId = asst.datasetId;
        datasetVersion = asst.datasetVersion;
        queryId = asst.queryId;
        operations = asst.operations;
        library = asst.library;
        i++;
      }
      turns.push({
        id: `turn-${i}`,
        question: q,
        answer: a,
        timestamp: t,
        streaming: isStream,
        latencyMs: latency,
        tableMarkdown,
        sqlQuery,
        pythonQuery,
        analyticalPlan,
        datasetName: datasetName || activeDoc?.filename,
        datasetId: datasetId || activeDoc?.doc_id,
        datasetVersion,
        queryId,
        operations,
        library
      });
    }
  }

  const docName = activeDoc?.filename || 'No dataset selected';
  const dbName = health?.database ? health.database.toUpperCase() : 'SQLITE';

  // 5 exact starter suggestions matching the design reference
  const topRowChips = [
    { label: 'Summarize key statistics', icon: Sparkles },
    { label: 'Find top 5 highest values', icon: BarChart2 },
    { label: 'Group data by categories', icon: Users },
  ];

  const bottomRowChips = [
    { label: 'Identify missing values', icon: Search },
    { label: 'Show trends and patterns', icon: TrendingUp },
  ];

  return (
    <div
      className="analysis-workspace-full-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        backgroundColor: '#f8fafc',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {/* ── SCROLLABLE WORKSPACE BODY (EXPANDED TO FULL VIEWPORT) ────────── */}
      <div
        className="analysis-scrollable-body"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 32px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: turns.length > 0 ? 'flex-start' : 'center',
          alignItems: 'center',
          gap: '20px'
        }}
      >
        {/* Turn Cards Feed OR Minimal Centered Empty State */}
        {turns.length > 0 ? (
          <div className="analysis-turns-feed" style={{ width: '100%', maxWidth: '1080px' }}>
            {turns.map((turn) => (
              <AnalysisTurnCard
                key={turn.id}
                question={turn.question}
                answer={turn.answer}
                timestamp={turn.timestamp}
                latencyMs={turn.latencyMs || (turn.streaming ? 0 : 18)}
                dbType={dbName}
                streaming={turn.streaming}
                tableMarkdown={turn.tableMarkdown}
                sqlQuery={turn.sqlQuery}
                pythonQuery={turn.pythonQuery}
                analyticalPlan={turn.analyticalPlan}
                datasetName={turn.datasetName || docName}
                datasetId={turn.datasetId || activeDoc?.doc_id}
                datasetVersion={turn.datasetVersion}
                queryId={turn.queryId}
                operations={turn.operations}
                library={turn.library}
                onClearChat={onClearChat}
              />
            ))}
          </div>
        ) : (
          <div
            className="analysis-starter-container"
            style={{
              width: '100%',
              maxWidth: '760px',
              padding: '20px 24px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {/* Centered Grid / Table Icon */}
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '14px',
                backgroundColor: '#eff6ff',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px',
                border: '1px solid #dbeafe',
                boxShadow: '0 2px 6px rgba(37, 99, 235, 0.08)'
              }}
            >
              <TableIcon size={26} strokeWidth={2.2} />
            </div>

            {/* Title */}
            <h2
              style={{
                fontFamily: 'var(--font-heading, sans-serif)',
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#0f172a',
                marginBottom: '8px',
                letterSpacing: '-0.01em'
              }}
            >
              Dataset Ready for Analysis
            </h2>

            {/* Subtitle Description */}
            <p
              style={{
                fontSize: '0.88rem',
                color: '#64748b',
                maxWidth: '560px',
                margin: '0 auto 28px',
                lineHeight: 1.55
              }}
            >
              Ask any question below. The AI will compute analytical answers and present them directly in structured row and column table format with sortable columns, CSV download, and charts.
            </p>

            {/* 5 Quick Suggestion Chips Arranged in 2 Clean Rows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center', width: '100%' }}>
              {/* Row 1: 3 chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'center' }}>
                {topRowChips.map((chip, idx) => {
                  const Icon = chip.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => onSendMessage(chip.label)}
                      disabled={isStreaming}
                      style={{
                        padding: '8px 16px',
                        fontSize: '0.82rem',
                        fontWeight: 600,
                        color: '#1e293b',
                        backgroundColor: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '10px',
                        cursor: isStreaming ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#eff6ff';
                        e.currentTarget.style.borderColor = '#93c5fd';
                        e.currentTarget.style.color = '#2563eb';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#ffffff';
                        e.currentTarget.style.borderColor = '#e2e8f0';
                        e.currentTarget.style.color = '#1e293b';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <Icon size={15} style={{ color: '#2563eb', flexShrink: 0 }} />
                      <span>{chip.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Row 2: 2 chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', justifyContent: 'center' }}>
                {bottomRowChips.map((chip, idx) => {
                  const Icon = chip.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => onSendMessage(chip.label)}
                      disabled={isStreaming}
                      style={{
                        padding: '8px 16px',
                        fontSize: '0.82rem',
                        fontWeight: 600,
                        color: '#1e293b',
                        backgroundColor: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '10px',
                        cursor: isStreaming ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
                        transition: 'all 0.15s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#eff6ff';
                        e.currentTarget.style.borderColor = '#93c5fd';
                        e.currentTarget.style.color = '#2563eb';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#ffffff';
                        e.currentTarget.style.borderColor = '#e2e8f0';
                        e.currentTarget.style.color = '#1e293b';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <Icon size={15} style={{ color: '#2563eb', flexShrink: 0 }} />
                      <span>{chip.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── BOTTOM COMMAND BAR (FIXED AT BOTTOM) ─────────────────────── */}
      <CommandBar
        activeDocName={docName}
        onSend={onSendMessage}
        onExportPDF={onExportPDF}
        disabled={isStreaming || !activeDoc}
      />
    </div>
  );
}
