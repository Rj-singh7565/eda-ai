# AI-Based EDA Assistant --- PDA

## Product & Design Architecture Specification

### 1. Product Vision

The AI-Based EDA Assistant is an enterprise-grade document intelligence
workspace for analyzing reports, financial statements, annual filings,
placement statistics, presentations, spreadsheets, and other data-heavy
documents.

The product combines a decoupled FastAPI backend with a Next.js/React
frontend. The frontend should feel like a professional analytical
application created by a product/design team rather than a generic AI
chatbot.

### 2. Frontend Design Direction

The interface must use a restrained, professional visual system.

#### Primary visual language

-   Main background: warm off-white / light stone.
-   Main surfaces: white and very light neutral gray.
-   Primary text: charcoal / near-black.
-   Secondary text: muted gray.
-   Accent: muted slate, charcoal, or desaturated blue.
-   Green must NOT be a dominant color.
-   Green may only appear in small semantic states such as:
    -   successful processing
    -   system health
    -   completed status
    -   small confirmation indicators
-   Do not use green for:
    -   large buttons
    -   large panels
    -   primary navigation
    -   large backgrounds
    -   charts as the default color
-   Avoid blue/purple AI gradients.
-   Avoid excessive glassmorphism.
-   Avoid neon effects.
-   Avoid oversized rounded cards.
-   Avoid excessive shadows.
-   Avoid decorative AI sparkle effects throughout the interface.

### 3. Design Principles

1.  Information first
2.  Human-designed editorial hierarchy
3.  Dense but readable analytical workspace
4.  Subtle animation rather than flashy animation
5.  Clear document/source relationships
6.  Strong typography and spacing
7.  Consistent component behavior
8.  Accessible contrast and keyboard navigation
9.  Responsive behavior
10. Professional enterprise software appearance

### 4. Main Application Layout

The desktop application uses a split-pane workspace.

#### Global Header

Contains:

-   EDA Assistant logo/wordmark
-   Global document search
-   Theme control
-   Notification/status indicator
-   User profile

The header should remain compact and should not dominate the workspace.

#### Left Navigation

Contains:

-   Home
-   Documents
-   Chats
-   Uploads
-   Settings
-   Help
-   Logout

The selected navigation item should use a subtle neutral background and
a small accent indicator rather than a large colored block.

#### Document Library

The document library provides:

-   Search
-   Document count
-   New document/upload action
-   Document list
-   File type indicator
-   File size
-   Last updated time
-   Processing state
-   Delete/more actions
-   Storage usage

Supported formats:

-   PDF
-   DOCX
-   PPTX
-   XLSX/XLS
-   CSV
-   TXT
-   Markdown
-   PNG/JPG/JPEG/BMP/TIFF
-   ZIP

ZIP archives may contain up to 15 supported files.

### 5. Main Document Workspace

The central workspace contains:

#### Document Header

Displays:

-   File type
-   Document name
-   Processing/ready state
-   File size
-   Indexed timestamp
-   Namespace status
-   View source action
-   Details action

#### Source / Markdown Viewer

The normalized Markdown representation should be readable as a real
document.

Features:

-   YAML metadata
-   Headings
-   Paragraphs
-   Lists
-   Tables
-   Source locations
-   Page/slide/row references
-   Scrollable reading area

The viewer should resemble a professional document reader, not a chat
interface.

### 6. AI Analysis Panel

The AI panel is integrated into the workspace.

It must support:

-   Natural-language questions
-   Streaming responses
-   Conversation history
-   Suggested questions
-   Citation chips
-   Source references
-   Confidence/relevance information
-   Follow-up questions

Example suggested questions:

-   Summarize the key findings
-   Show the revenue trend
-   Find unusual changes
-   Compare two years
-   Find the most important table

The answer area should use simple message containers with restrained
styling.

### 7. Citation System

Every grounded answer should be able to expose citations.

Citation chips may show:

-   Page
-   Slide
-   Table
-   Row
-   Source document

Clicking a citation opens a citation drawer.

The citation drawer should contain:

-   Document name
-   Source location
-   Retrieved text/context
-   Highlighted evidence
-   Retrieval confidence score

The drawer should slide in smoothly from the right.

### 8. Processing Pipeline UI

The frontend displays ingestion stages:

1.  Parsing
2.  Chunking
3.  Embedding
4.  Indexing
5.  Ready

Each stage displays:

-   Status
-   Completion indicator
-   Current stage
-   Error state where applicable

Animation should be subtle:

-   Small progress transitions
-   Spinners for active processing
-   Fade/slide transitions
-   No continuous decorative animation

### 9. Upload Experience

The upload zone supports:

-   Drag and drop
-   File browser
-   Multiple files
-   ZIP archives
-   Upload progress
-   Processing state

The upload area should visually communicate that it is functional
software, not a marketing hero section.

Maximum file size:

-   25 MB

Maximum ZIP contents:

-   15 files

### 10. Responsive Behavior

#### Desktop

Use:

-   Navigation
-   Document library
-   Document viewer
-   AI analysis panel
-   Citation drawer

#### Tablet

Collapse secondary information panels while keeping:

-   Document navigation
-   Main document area
-   AI assistant

#### Mobile

Use:

-   Compact header
-   Drawer-based document navigation
-   Full-width document viewer
-   Full-width chat interface
-   Bottom-sheet or drawer citations

### 11. Animation System

Animations must improve usability.

Allowed:

-   150--300 ms transitions
-   Message entrance
-   Drawer slide-in
-   Modal fade
-   Button hover
-   Upload hover state
-   Processing spinner
-   Progress bar movement
-   Small status transitions

Avoid:

-   Constant floating elements
-   Large animated gradients
-   Excessive bounce effects
-   Parallax
-   Flashing effects
-   Continuous decorative particles

### 12. Color System

Recommended default palette:

-   Canvas: `#F4F2ED`
-   Surface: `#FBFAF7`
-   Elevated surface: `#FFFEFB`
-   Border: `#DFDDD5`
-   Strong border: `#D1CEC4`
-   Primary text: `#242521`
-   Secondary text: `#77776F`
-   Soft neutral: `#ECEAE4`
-   Primary accent: muted slate / charcoal
-   Success: muted green, used only for semantic status
-   Warning: muted amber
-   Error: muted red

Green usage should remain intentionally limited.

### 13. Backend Integration

The frontend must connect to the existing FastAPI backend.

Required endpoints:

-   `GET /health`
-   `POST /upload`
-   `GET /status/{doc_id}`
-   `GET /documents`
-   `GET /documents/{doc_id}/history`
-   `GET /documents/{doc_id}/markdown`
-   `DELETE /documents/{doc_id}`
-   `POST /ask/stream`

The Q&A endpoint uses SSE streaming.

### 14. RAG UX

The frontend should reflect the actual RAG pipeline:

1.  User selects a document.
2.  User submits a question.
3.  Query is embedded.
4.  Pinecone is queried within the document namespace.
5.  Low-confidence results below the configured similarity threshold are
    filtered.
6.  Retrieved context is passed to the LLM.
7.  The answer streams token-by-token.
8.  Citations are rendered beside the answer.
9.  Clicking a citation opens exact source context.

Configured defaults:

-   Embedding model: `bge-small-en-v1.5`
-   Embedding dimension: 384
-   Chunk size: 600 characters
-   Chunk overlap: 80 characters
-   Top K: 5
-   Similarity threshold: 0.35
-   Memory turns: 4

### 15. Technical Frontend Stack

-   Next.js 14
-   React 18
-   TypeScript
-   Vanilla CSS / CSS custom properties
-   App Router

Avoid unnecessary UI libraries unless they provide a clear production
benefit.

### 16. Component Structure

``` text
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/
│   ├── DocumentSidebar.tsx
│   ├── UploadZone.tsx
│   ├── ProcessingStatus.tsx
│   ├── DocumentHeader.tsx
│   ├── ChatWindow.tsx
│   ├── ChatMessage.tsx
│   ├── ChatInput.tsx
│   ├── CitationCard.tsx
│   └── DocumentViewer.tsx
└── lib/
    ├── api.ts
    └── types.ts
```

### 17. Human-Designed UI Rules

The final interface should look like a serious internal
analytics/productivity application.

Do:

-   Use asymmetrical but balanced spacing.
-   Use typography to create hierarchy.
-   Keep cards relatively flat.
-   Use borders more than shadows.
-   Use neutral colors as the majority of the interface.
-   Keep icons simple.
-   Use color to communicate state.
-   Keep buttons compact.
-   Keep the document content visually dominant.

Do not:

-   Use a purple/blue AI gradient.
-   Make every element a rounded card.
-   Use green as the main brand color.
-   Put huge AI sparkles around the interface.
-   Use excessive glass effects.
-   Use giant headings.
-   Use fake dashboard metrics without meaning.
-   Make the interface resemble a generic chatbot.

### 18. Accessibility

The UI must support:

-   Keyboard navigation
-   Visible focus states
-   Accessible button labels
-   Sufficient text contrast
-   Reduced-motion preference
-   Semantic HTML
-   Screen-reader-friendly status messages

### 19. Product Goal

The final frontend should communicate:

> "This is a professional document analysis tool with an AI reasoning
> layer."

It should not communicate:

> "This is an AI demo generated from a UI template."

The document itself, source evidence, retrieval information, and
analytical workflow should remain the visual focus.
