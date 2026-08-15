# EDA Assistant — Project Rules

## UI Design & Layout
- **Preserve the current split-pane layout**: left sidebar (340px) with document list + upload zone, right main workspace with chat interface.
- **Keep the existing dark/light theme system** using CSS custom properties (`--bg-app`, `--bg-sidebar`, `--accent-primary`, etc.).
- **Maintain the current design language**: Inter font family, indigo/violet accent colors (`#6366f1`), rounded corners (10-14px), smooth transitions, toast notifications, citation side drawer, and Markdown preview modal.
- **Do not introduce CSS frameworks** (e.g., Tailwind, Bootstrap) — use vanilla CSS with the existing variable-based design system.
- **Keep chat bubble styles**: blue right-aligned user bubbles, bordered left-aligned assistant bubbles with citation chips.
- **Preserve drag-and-drop upload zone**, ingestion progress bar, document action buttons (Markdown view, delete), and status badges.
