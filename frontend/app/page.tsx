import React, { Suspense } from 'react';
import {
  getServerDocuments,
  getServerDashboardStats,
  getServerSystemHealth,
  getServerChatHistory,
} from '../lib/server/api';
import DashboardClientContainer from '../components/DashboardClientContainer';
import DashboardLoading from './loading';

export const dynamic = 'force-dynamic'; // Ensures fresh server-rendered data on each request

/**
 * Server Component: EDA Assistant Workspace Shell.
 * Executes on the Next.js server, pre-fetching initial documents, statistics, system health,
 * and conversational history prior to streaming HTML to the browser.
 */
export default async function DashboardPage() {
  // Concurrent server-side fetches directly from FastAPI
  const [documents, stats, health] = await Promise.all([
    getServerDocuments(),
    getServerDashboardStats(),
    getServerSystemHealth(),
  ]);

  // Pre-fetch initial chat history for the first document if available
  const activeDocId = documents.length > 0 ? documents[0].doc_id : null;
  const initialHistory = activeDocId ? await getServerChatHistory(activeDocId) : { history: [] };

  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardClientContainer
        initialDocuments={documents}
        initialStats={stats}
        initialHealth={health}
        initialHistory={initialHistory?.history || []}
      />
    </Suspense>
  );
}
