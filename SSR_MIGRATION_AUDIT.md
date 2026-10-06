# SSR Migration Audit — EDA Assistant

## 1. Executive Summary

This audit assesses the rendering architecture of the enterprise **AI-Based EDA Assistant** frontend (Next.js 14 App Router) and establishes the migration pathway from browser-first client rendering to a **Server-First Hybrid Rendering architecture**.

### Baseline Audit Metrics
- **Current Page Architecture:** 100% Client-side page (`app/page.tsx` marked `'use client'`).
- **Initial First Load JavaScript:** 121 kB (Page: 33.5 kB, Shared: 87.2 kB).
- **Initial Post-Hydration Browser Requests:** 5 waterfall HTTP requests on page load (`/api/documents`, `/api/stats`, `/api/health`, `/api/documents/{id}/markdown`, `/api/chat/{id}/history`).
- **Initial Server-Rendered HTML Content:** Empty UI shells with 0 datasets, null stats, and empty tables prior to browser-side fetch completion.
- **Suspense Boundaries:** 0.
- **Server Data Access Layer:** None (all fetches originate from browser client code via `lib/api.ts`).

---

## 2. Component Inventory & Classification

| Component | Current Rendering Mode | Reason | Can Become Server Component? | Data Dependencies | Interactive Dependencies | Migration Risk |
|---|---|---|---|---|---|---|
| `app/layout.tsx` | Server Component | Root layout, HTML, meta tags, fonts | Already Server Component | None | None | None |
| `app/page.tsx` | Client Component | Contains `'use client'`, state for navigation, active doc, chats | **YES (Hybrid Page Shell)** | FastAPI `/api/documents`, `/api/stats`, `/api/health`, `/api/chat/{id}/history` | Delegated to client leaf components | Low |
| `app/loading.tsx` | Missing | New loading state file | **YES (Server Component)** | None | None | None |
| `app/error.tsx` | Missing | New error boundary file | **Client Component** (Next.js requirement) | Error object, reset callback | Reset button click | Low |
| `app/not-found.tsx` | Missing | New not found page | **YES (Server Component)** | None | Navigation links | None |
| `components/dashboard/StorageView.tsx` | Client Component | Marked `'use client'` arbitrarily | **YES (100% Server Component)** | `documents`, `stats`, `health` | None (pure presentation) | None |
| `components/dashboard/SettingsView.tsx` | Client Component | Marked `'use client'` arbitrarily | **YES (100% Server Component)** | `health` | None (read-only presentation) | None |
| `components/dashboard/HistoryView.tsx` | Client Component | Displays conversation turns | **YES (Hybrid / Server-ready presentation)** | `messages`, `activeDoc` | `onOpenAnalysis` button | Low |
| `components/dashboard/OverviewDashboard.tsx` | Client Component | KPI cards, storage progress, upload dropzone, recent table | **Hybrid (Server KPI/Metrics + Client Upload/Action Islands)** | `stats`, `documents`, `activeDoc` | Dropzone, file input, row action menu, navigation tabs | Low |
| `components/dashboard/DatasetsView.tsx` | Client Component | Dataset list, filter chips, search input, upload button | **Client Component (Receives SSR Initial Data)** | `documents`, `activeDocId` | Live text search, format filters, delete/preview actions, upload | Low |
| `components/NavSidebar.tsx` | Client Component | Left rail navigation, tab switcher | **Client Component** | `activeTab`, `activeDoc` | Tab selection handlers, preview modal trigger | Low |
| `components/GlobalHeader.tsx` | Client Component | Top navigation bar with active dataset selector and export | **Client Component** | `activeTab`, `activeDoc`, `documents` | Dataset dropdown, notification popup, export modal trigger | Low |
| `components/analysis/AnalysisWorkspace.tsx` | Client Component | Active EDA analysis surface, turn feed, starter chips | **Client Component** | `documents`, `activeDoc`, `messages`, `health` | Turn feed rendering, starter suggestion clicks, clear chat | Low |
| `components/analysis/AnalysisTurnCard.tsx` | Client Component | Per-turn analytics card with virtualized tables, charts, SQL, stopwatch | **Client Component** | `question`, `answer`, `timestamp`, `latencyMs` | Tab switching ('table'/'chart'/'sql'), `@tanstack/react-virtual`, sorting, clipboard, PDF print | Low |
| `components/analysis/CommandBar.tsx` | Client Component | Natural language question input | **Client Component** | `activeDocName` | Input text state, Enter keypress, form submission | None |
| `components/UploadZone.tsx` | Client Component | Drag-and-drop file ingestion zone | **Client Component** | None | HTML5 drag-and-drop, file input ref, `onUpload` callback | None |
| `components/DocumentViewer.tsx` | Client Component | Modal preview for canonical Markdown | **Client Component** | `filename`, `markdownContent` | Clipboard copy API, Blob download API, Close event | None |
| `components/ExportModal.tsx` | Client Component | Multi-format analysis report exporter | **Client Component** | `activeDoc`, `messages` | Blob generation (PDF, Excel, CSV, JSON, MD), file downloads | None |
| `components/DocumentSidebar.tsx` | Client Component | Split-pane document list and filter | **Client Component** | `documents`, `activeDocId` | Search filter state, document selection, deletion | Low |
| `components/DocumentHeader.tsx` | Client Component | Active document metadata chip | **Client Component (or Server Island)** | `activeDoc` | Preview modal trigger | Low |
| `components/DocumentWorkspaceReader.tsx` | Client Component | Markdown / tabular source reader | **Client Component** | `markdownContent` | Copy, download actions | Low |
| `components/EvidenceRuler.tsx` | Client Component | Grounding confidence ruler | **Server / Client Component** | `score` | None (pure SVG/CSS bar) | None |
| `components/SourceViewer.tsx` | Client Component | Dual tab source viewer (Markdown / Table) | **Client Component** | `markdownContent`, `tableData` | Tab selection, coordinate highlight | Low |
| `components/CitationsPanel.tsx` | Client Component | Grounding evidence drawer | **Client Component** | `citations`, `isOpen` | Drawer open/close, jump to coordinate | Low |
| `components/CitationCard.tsx` | Client Component | Individual citation card | **Client Component** | `citation` | Expand/collapse snippet, copy | Low |
| `components/ChatWindow.tsx` | Client Component | Message feed container | **Client Component** | `messages` | Auto-scroll `useRef` and `useEffect` | Low |
| `components/ChatMessage.tsx` | Client Component | Chat bubble with citation chips | **Client Component** | `message` | Citation drawer toggle | Low |
| `components/ChatInput.tsx` | Client Component | Chat prompt input box | **Client Component** | None | Form submit, textarea auto-expand | None |
| `components/ProcessingStatus.tsx` | Client Component | Document ingestion status indicator | **Server / Client Component** | `status` | None (pure CSS animation) | None |

---

## 3. Data Flow & Waterfall Analysis

### Current Browser-Side Waterfall (Anti-Pattern):
```text
1. Browser requests GET /
2. Server returns static shell HTML (empty state, 0 datasets, null stats)
3. Browser downloads 121 kB JS bundle
4. Browser executes React hydration
5. useEffect() triggers:
   ├── GET /api/documents (wait ~25ms)
   ├── GET /api/stats (wait ~20ms)
   └── GET /api/health (wait ~15ms)
6. React state updates -> Component re-renders
7. Second useEffect(activeDocId) triggers:
   ├── GET /api/documents/{id}/markdown (wait ~30ms)
   └── GET /api/chat/{id}/history (wait ~18ms)
8. Final UI becomes populated (~150-300ms after initial HTML arrives)
```

### Target Server-First Hybrid Flow:
```text
1. Browser requests GET /
2. Next.js Server Component concurrently retrieves directly from FastAPI:
   ├── getDocuments()
   ├── getDashboardStats()
   ├── getSystemHealth()
   └── getChatHistory(activeDocId)
3. Server streams fully populated HTML with initial datasets, KPIs, storage, and history
4. Browser renders instant First Contentful Paint (FCP) and Largest Contentful Paint (LCP)
5. Only interactive client components hydrate (CommandBar, UploadZone, AnalysisTurnCard, Dropdowns)
6. Zero post-hydration network requests required for initial view
7. Live SSE streaming (/api/chat/stream) activates seamlessly on user query submission
```

---

## 4. Security & Environment Variable Separation

- **Private Backend URL:** Server-side fetching uses `INTERNAL_API_URL` or `FASTAPI_URL` (defaulting to `http://127.0.0.1:8000` or `http://localhost:8000`) on the server.
- **Client API URL:** Browser client components continue using `NEXT_PUBLIC_API_URL` for SSE streaming (`/api/chat/stream`) and file uploads (`/api/documents/upload`).
- **Zero Secret Leakage:** Database paths, Pinecone keys, and Groq credentials remain isolated inside FastAPI and server environment variables.

---

## 5. Migration Strategy & Boundaries

1. **Server Data Access Layer (`frontend/lib/server/api.ts`):**
   - Create type-safe, direct server fetch functions: `getServerDocuments()`, `getServerStats()`, `getServerHealth()`, `getServerHistory()`, `getServerMarkdown()`.
   - Implement Next.js caching with tag revalidation (`next: { tags: ['documents', 'stats'] }`).

2. **Server-Rendered Page Shell (`frontend/app/page.tsx`):**
   - Convert `app/page.tsx` from `'use client'` to an async Server Component.
   - Fetch initial data on the server with graceful fallback so a down backend renders a clean server-side offline banner rather than crashing.
   - Mount `<Suspense>` boundaries with matching skeleton dimensions for Dashboard, Datasets, and Analysis.

3. **Interactive Client Workspace Island (`frontend/components/DashboardClientContainer.tsx`):**
   - Encapsulate interactive state (active tabs, active document selection, live SSE streaming, upload handlers, deletion, toast notifications).
   - Initialize state directly from the server-provided props (`initialDocuments`, `initialStats`, `initialHealth`, `initialHistory`), eliminating post-mount fetch waterfalls.

4. **Convert Pure Presentation Components to Server Components:**
   - Remove `'use client'` from `StorageView.tsx` and `SettingsView.tsx`.
   - Modularize `OverviewDashboard.tsx` so static KPI metrics and health scores render on the server.

5. **Loading & Error Infrastructure:**
   - Implement `app/loading.tsx` with skeleton layout matching the 5-tab application shell.
   - Implement `app/error.tsx` for error boundaries without crashing the application.
   - Implement `app/not-found.tsx`.
