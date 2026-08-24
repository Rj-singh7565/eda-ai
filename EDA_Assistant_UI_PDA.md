# EDA Assistant — UI PDA
## Product Design Architecture & Frontend Specification

**File name:** `PDA.md`

---

## 1. Product Identity

### Product name
**EDA Assistant**

### Product positioning
A professional document-intelligence workspace for exploring reports, spreadsheets, presentations, financial statements, placement statistics, and other data-heavy documents through grounded AI analysis.

### Core design idea
The interface is designed as an **evidence workspace**, not as a generic AI chatbot.

The primary relationship is:

**Document → Evidence → Analysis → Citation**

The document remains the visual center of the product while the AI assistant works beside it.

---

# 2. UI Design Direction

The interface should feel like software created for analysts, researchers, finance teams, academic teams, and enterprise users.

It should NOT resemble:

- a generic ChatGPT clone
- an AI landing page
- a template dashboard
- a neon AI interface
- a purple/blue gradient SaaS template

The design should communicate:

> Serious document analysis with an AI reasoning layer.

---

# 3. Visual Identity

## 3.1 Color Strategy

Green must not be the dominant brand color.

### Primary palette

| Token | Value | Usage |
|---|---|---|
| Canvas | `#F1F0EC` | Main application background |
| Surface | `#F8F8F5` | Navigation and panels |
| Paper | `#FFFEFA` | Document/source surfaces |
| Ink | `#181B1D` | Primary text |
| Muted | `#72777B` | Secondary text |
| Slate | `#4B6170` | Primary UI accent |
| Soft Slate | `#E7EDF0` | Selected states |
| Border | `#D9DCDA` | Dividers and component borders |
| Success | `#647C67` | Small ready/healthy indicators only |
| Warning | `#A97945` | Processing/warning states |
| Error | `#9A5C5C` | Errors |

### Green restriction

Green may only be used for:

- Ready status
- Healthy API status
- Successful processing
- Small completion indicators

Green must NOT be used for:

- Main navigation
- Main CTA
- Large backgrounds
- Primary brand identity
- Large charts
- Hero sections

The dominant visual language is neutral + slate.

---

# 4. Typography

Use three type roles.

## Display / Headings

**Space Grotesk**

Used for:

- Application headings
- Document title
- Section titles
- Major interface labels

## Body / Interface

**DM Sans**

Used for:

- Navigation
- Chat messages
- Buttons
- Metadata
- General UI text

## Data / Technical

**IBM Plex Mono**

Used for:

- Page numbers
- Source coordinates
- Metadata
- File status
- Technical labels
- Evidence references
- Retrieval scores

Typography should create hierarchy instead of relying on large colored cards.

---

# 5. Desktop Layout

The desktop application uses four functional areas:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ EDA Assistant       Global Search                         API   User          │
├──────────────┬───────────────────────────────────────┬──────────────┬───────┤
│              │                                       │              │       │
│ Navigation   │ Document Library / Source             │ AI Analysis  │ Cite  │
│              │                                       │              │       │
│ Documents    │ ┌─────────────────────────────────┐   │ Questions    │ Source│
│ Chats        │ │ Annual Report 2025              │   │ Answers      │ cards │
│ Uploads      │ │                                 │   │ Citations    │       │
│ Settings     │ │ Financial Performance           │   │ Composer     │       │
│              │ │                                 │   │              │       │
│              │ │ Tables / Charts / Text          │   │              │       │
│              │ │                                 │   │              │       │
│              │ └─────────────────────────────────┘   │              │       │
└──────────────┴───────────────────────────────────────┴──────────────┴───────┘
```

Recommended desktop widths:

- Navigation: approximately 210–250px
- Document/library area: approximately 220–280px when present
- Main source area: flexible
- AI assistant: approximately 320–380px
- Citation drawer: approximately 320–420px when opened

---

# 6. Global Header

The header should be compact.

### Contains

- EDA Assistant identity
- Global document search
- API/system health
- Theme control
- User profile

### Example

```text
[EDA Assistant]
document intelligence / evidence workspace

             [ Search across documents... ]       API healthy   RS
```

The header must not become a marketing hero.

---

# 7. Navigation

Primary navigation:

- Overview
- Documents
- Conversations
- Upload queue
- Settings

Secondary navigation:

- Help
- Logout
- User profile

The active navigation item uses:

- subtle slate-tinted background
- dark text
- small visual emphasis

Avoid large colored navigation blocks.

---

# 8. Document Library

The document library is a working tool, not decorative content.

### Features

- Document search/filter
- File type indicator
- File name
- File size
- Last updated time
- Ready/processing state
- More/delete action
- Storage usage
- Upload action

### Example

```text
DOCUMENTS                         +

[ Search / filter ]

PDF   Annual Report 2025.pdf
      4.8 MB · 2 min ago              ●

XLSX  Placement Statistics.xlsx
      1.2 MB · 8 min ago              ●

PPTX  Q4 Investor Deck.pptx
      8.1 MB · 18 min ago             ●
```

File-type colors should remain muted and semantic.

---

# 9. Upload Experience

The upload area should be functional and compact.

### Supported formats

- PDF
- DOCX
- PPTX
- XLSX
- XLS
- CSV
- TXT
- Markdown
- PNG
- JPG
- JPEG
- BMP
- TIFF
- ZIP

### Limits

- Maximum file size: 25 MB
- Maximum ZIP files: 15

### Upload UI

```text
┌─────────────────────────────────────────┐
│             Upload documents            │
│                                         │
│        Drag & drop files here           │
│                                         │
│        PDF · DOCX · XLSX · ZIP          │
│                                         │
│             [ Browse Files ]             │
└─────────────────────────────────────────┘
```

The drop zone should respond with a subtle border/background transition.

---

# 10. Document Header

When a document is selected:

```text
[PDF]

ACTIVE SOURCE
Annual Report 2025.pdf       ● Ready
4.8 MB · indexed just now · isolated namespace

[ Read source ] [ Metadata ]
```

The header should expose document state without becoming visually heavy.

---

# 11. Source Viewer

The source document is the visual center.

The viewer should look like a real analytical document.

### Features

- Source tab
- Preview tab
- Metadata tab
- Page position
- Normalized Markdown
- Headings
- Paragraphs
- Tables
- Figures/charts
- Source references

### Example

```text
SOURCE       PREVIEW       METADATA                     p. 12 / 64

┌──────────────────────────────────────────────────────────────┐
│ ANNUAL REPORT / FY2025                                       │
│                                                              │
│ Financial performance                                        │
│                                                              │
│ Revenue expanded during FY2025...                            │
│                                                              │
│ ──────────────────────────────────────────────────────────── │
│                                                              │
│ 12.04   Revenue composition                                  │
│                                                              │
│ Enterprise       FY2024       FY2025       +34.8%             │
│ Services         FY2024       FY2025       +27.1%             │
│                                                              │
│                    Revenue trajectory                         │
│                    █                                         │
│                █   █                                         │
│            █   █   █                                         │
│           2023 2024 2025                                     │
└──────────────────────────────────────────────────────────────┘
```

The source surface should use a paper-like neutral background.

---

# 12. Signature UI Element — Evidence Ruler

The unique visual element of this interface is the **Evidence Ruler**.

It appears beside the document.

```text
EVIDENCE

  03
   •
  11
   •
  18  ◀ active
   •
  27
   •
  41
```

The ruler represents source coordinates referenced by the AI response.

### Behavior

Selecting an evidence coordinate opens the citation drawer.

This makes the visual language directly connected to the RAG workflow.

It is not decorative.

---

# 13. AI Analysis Panel

The AI panel should be presented as a research instrument.

### Header

```text
ANALYSIS
Ask the source

streaming ready
```

### Conversation

User messages and AI answers should remain visually restrained.

User:

```text
What were the main drivers of revenue growth in FY2025?
```

Assistant:

```text
Revenue growth was mainly supported by stronger
enterprise sales and a higher contribution from
services.

[p. 18 →] [p. 27 →] [p. 41 →]
```

Citation chips should be small and technical.

---

# 14. Suggested Questions

Provide a few contextual shortcuts:

- Key findings
- Revenue trend
- Unusual changes
- Compare two years
- Find the largest table
- Summarize this section

Avoid excessive suggestions.

---

# 15. Chat Composer

The composer should be compact.

```text
┌──────────────────────────────────────────────┐
│ Ask about this document...                   │
│                                              │
│                               [ Send → ]     │
└──────────────────────────────────────────────┘

Answers are generated from retrieved source passages.
```

The composer must not dominate the page.

---

# 16. Citation Drawer

When a citation is selected, a right-side drawer opens.

### Citation content

- Source document
- Page/slide/table coordinate
- Retrieved context
- Highlighted evidence
- Retrieval score

Example:

```text
SOURCE COORDINATE

p. 18
Annual Report 2025.pdf

────────────────────────

Revenue composition

The report attributes the change primarily
to stronger enterprise sales and a larger
services contribution.

────────────────────────

Retrieval score                 0.87
```

The drawer slides in from the right.

---

# 17. Citation Types

Support:

- Page
- Slide
- Table
- Figure
- Row
- Text chunk

Citation labels should use technical but understandable language.

Examples:

- `p. 18`
- `Table 3.1`
- `Fig. 4`
- `Slide 14`
- `Row 42`

---

# 18. Document Snapshot

A secondary metadata area may show:

```text
DOCUMENT SNAPSHOT

Pages       64
Chunks      286
Tables      19
```

Keep this secondary to the document itself.

---

# 19. Processing Pipeline

The interface should expose ingestion progress:

```text
Parsing       ✓ Complete
Chunking      ✓ Complete
Embedding     ✓ Complete
Indexing      ✓ Complete
Ready         ●
```

Processing animation should use a small spinner or progress transition.

Avoid large animated progress graphics.

---

# 20. RAG Interaction Flow

The UI reflects the real backend flow:

```text
Select document
      ↓
Ask question
      ↓
Embed query
      ↓
Search document namespace
      ↓
Filter low-confidence matches
      ↓
Generate grounded answer
      ↓
Stream answer
      ↓
Display citations
      ↓
Open exact source evidence
```

The frontend should make this relationship understandable without exposing internal implementation details to normal users.

---

# 21. Backend API Compatibility

The frontend must support the existing FastAPI endpoints:

```text
GET    /health
POST   /upload
GET    /status/{doc_id}
GET    /documents
GET    /documents/{doc_id}/history
GET    /documents/{doc_id}/markdown
DELETE /documents/{doc_id}
POST   /ask/stream
```

`POST /ask/stream` should be handled as an SSE streaming response.

---

# 22. Frontend Architecture

Recommended structure:

```text
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
│
├── components/
│   ├── AppHeader.tsx
│   ├── Navigation.tsx
│   ├── DocumentLibrary.tsx
│   ├── UploadZone.tsx
│   ├── ProcessingStatus.tsx
│   ├── DocumentHeader.tsx
│   ├── DocumentViewer.tsx
│   ├── EvidenceRuler.tsx
│   ├── ChatWindow.tsx
│   ├── ChatMessage.tsx
│   ├── ChatInput.tsx
│   ├── CitationDrawer.tsx
│   └── DocumentMetadata.tsx
│
└── lib/
    ├── api.ts
    └── types.ts
```

---

# 23. Responsive Design

## Desktop

Show:

- Navigation
- Document library
- Source viewer
- AI assistant
- Evidence ruler

## Tablet

Collapse secondary navigation and metadata.

Maintain:

- Source viewer
- AI assistant
- Document switching

## Mobile

Use drawers for:

- Navigation
- Document list
- AI assistant
- Citations

The source document should remain readable and full-width.

---

# 24. Motion Design

Motion should be deliberate.

### Use

- 150–300ms transitions
- Citation drawer slide
- Source loading fade
- Message entrance
- Upload state transition
- Processing spinner
- Button hover
- Active evidence transition

### Avoid

- Floating particles
- Neon animations
- Constant moving gradients
- Excessive bouncing
- Parallax
- Animated AI sparkles
- Large decorative motion

### Accessibility

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

---

# 25. Interaction Language

Use plain user-facing terminology.

Prefer:

- Read source
- Ask about this document
- View evidence
- Compare years
- Browse files
- Remove document
- View citations

Avoid exposing implementation terminology such as:

- Vector namespace
- Embedding pipeline
- Webhook
- Chunk retrieval configuration

Those are implementation concepts, not primary user controls.

---

# 26. Empty States

Empty states should guide the user.

Example:

```text
No documents yet.

Add a report, spreadsheet, presentation,
or ZIP archive to start asking questions.

[ Add documents ]
```

Do not use vague text such as:

> Nothing here yet.

---

# 27. Error States

Errors should be direct and actionable.

Example:

```text
This file is larger than 25 MB.

Choose a smaller file or split the document
before uploading.

[ Choose another file ]
```

Avoid generic:

> Something went wrong.

---

# 28. Accessibility

The frontend must support:

- Keyboard navigation
- Visible focus states
- Semantic buttons
- Screen-reader labels
- Accessible status announcements
- Sufficient contrast
- Reduced motion
- Responsive text sizing

---

# 29. Design Quality Rules

The interface must not become visually noisy.

### Keep

- One dominant visual idea
- Neutral surfaces
- Strong typography
- Functional borders
- Small technical labels
- Real document content
- Evidence-driven interactions

### Remove

- Decorative gradients
- Excessive cards
- Excessive rounded corners
- Large shadows
- Generic AI icons
- Unnecessary metrics
- Fake activity indicators
- Excessive green

---

# 30. Final Design Thesis

The product should feel like:

**A serious research desk for documents, with AI sitting beside the evidence.**

The document is primary.

The evidence is traceable.

The AI is useful because it points back to the source.

The visual identity should therefore be remembered for its:

**Evidence Ruler + document-first workspace + restrained slate analytical language.**

---

## 31. Implementation Stack

- Next.js 14
- React 18
- TypeScript
- Vanilla CSS / CSS custom properties
- FastAPI backend
- SSE streaming
- Existing RAG/Pinecone/Groq architecture

The frontend should remain decoupled from the backend and communicate through the documented API layer.
