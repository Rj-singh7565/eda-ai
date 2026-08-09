/* ==========================================================================
   AI-BASED EDA ASSISTANT — FRONTEND SCRIPT (STATE & SSE STREAMING)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // ── App State ────────────────────────────────────────────────────────
    const state = {
        documents: [],
        activeDocId: null,
        theme: localStorage.getItem("eda_theme") || "dark",
        pollingIntervals: {}
    };

    // ── DOM References ───────────────────────────────────────────────────
    const body = document.body;
    const themeToggleBtn = document.getElementById("theme-toggle");
    
    // Sidebar & Upload
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const ingestionProgress = document.getElementById("ingestion-progress");
    const progressFilename = document.getElementById("progress-filename");
    const progressPercent = document.getElementById("progress-percent");
    const progressFill = document.getElementById("progress-fill");
    const progressStatus = document.getElementById("progress-status");
    const docsList = document.getElementById("docs-list");
    const docsCount = document.getElementById("docs-count");

    // Main Workspace & Header
    const activeDocTitle = document.getElementById("active-doc-title");
    const metaPages = document.getElementById("meta-pages");
    const metaChunks = document.getElementById("meta-chunks");
    const metaStatus = document.getElementById("meta-status");

    // Chat Containers
    const chatContainer = document.getElementById("chat-container");
    const emptyState = document.getElementById("empty-state");
    const docWelcomeChips = document.getElementById("doc-welcome-chips");
    const chatMessages = document.getElementById("chat-messages");
    const chatForm = document.getElementById("chat-form");
    const questionInput = document.getElementById("question-input");
    const sendBtn = document.getElementById("send-btn");

    // Citation Side Drawer
    const citationDrawer = document.getElementById("citation-drawer");
    const drawerBackdrop = document.getElementById("drawer-backdrop");
    const drawerPages = document.getElementById("drawer-pages");
    const drawerScore = document.getElementById("drawer-score");
    const drawerContent = document.getElementById("drawer-content");
    const closeDrawerBtn = document.getElementById("close-drawer");

    // Toast Container
    const toastContainer = document.getElementById("toast-container");

    // ── 1. Theme Management ──────────────────────────────────────────────
    function applyTheme(theme) {
        state.theme = theme;
        localStorage.setItem("eda_theme", theme);
        body.className = theme === "dark" ? "theme-dark" : "theme-light";
    }
    applyTheme(state.theme);

    themeToggleBtn.addEventListener("click", () => {
        applyTheme(state.theme === "dark" ? "light" : "dark");
    });

    // ── 2. Toast Notifications ───────────────────────────────────────────
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ── 3. Document Registry & Polling ───────────────────────────────────
    async function fetchDocuments() {
        try {
            const res = await fetch("/documents");
            if (!res.ok) throw new Error("Failed to load documents.");
            state.documents = await res.json();
            renderDocumentsList();
            
            // If active document is not set or deleted, default to first ready document or null
            if (!state.activeDocId || !state.documents.some(d => d.doc_id === state.activeDocId)) {
                const firstReady = state.documents.find(d => d.status === "ready") || state.documents[0];
                selectActiveDocument(firstReady ? firstReady.doc_id : null, false);
            }
        } catch (err) {
            console.error("fetchDocuments error:", err);
            showToast("Failed to connect to backend server.", "error");
        }
    }

    function updateActiveDocItemStyles() {
        document.querySelectorAll(".doc-item").forEach(item => {
            if (item.dataset.docId === state.activeDocId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    }

    function renderDocumentsList() {
        docsList.innerHTML = "";
        docsCount.textContent = state.documents.length;

        if (state.documents.length === 0) {
            docsList.innerHTML = `<li class="empty-docs-text" style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 12px;">No documents uploaded yet.</li>`;
            updateActiveDocDetails(null);
            return;
        }

        state.documents.forEach(doc => {
            const li = document.createElement("li");
            li.className = `doc-item ${doc.doc_id === state.activeDocId ? "active" : ""}`;
            li.dataset.docId = doc.doc_id;

            const statusClass = `status-${doc.status}`;

            li.innerHTML = `
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta-tags">
                        <span>${doc.page_count || 0} pgs</span>
                        <span class="status-badge ${statusClass}">${doc.status}</span>
                    </div>
                </div>
                <button class="doc-delete-btn" title="Delete document" aria-label="Delete document">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            `;

            // Document click -> select active
            li.addEventListener("click", (e) => {
                if (e.target.closest(".doc-delete-btn")) return;
                selectActiveDocument(doc.doc_id);
            });

            // Delete click
            const delBtn = li.querySelector(".doc-delete-btn");
            delBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (confirm(`Delete "${doc.filename}" and its vectors?`)) {
                    await deleteDocument(doc.doc_id);
                }
            });

            docsList.appendChild(li);

            // If document is processing, ensure polling is active
            if (doc.status !== "ready" && doc.status !== "failed" && !state.pollingIntervals[doc.doc_id]) {
                startStatusPolling(doc.doc_id);
            }
        });

        updateActiveDocItemStyles();
    }

    async function deleteDocument(docId) {
        try {
            const res = await fetch(`/documents/${docId}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Delete failed.");
            
            if (state.pollingIntervals[docId]) {
                clearInterval(state.pollingIntervals[docId]);
                delete state.pollingIntervals[docId];
            }

            showToast("Document deleted successfully.", "success");
            if (state.activeDocId === docId) {
                state.activeDocId = null;
            }
            await fetchDocuments();
        } catch (err) {
            showToast("Failed to delete document.", "error");
        }
    }

    function selectActiveDocument(docId, shouldRefreshList = false) {
        state.activeDocId = docId;
        updateActiveDocItemStyles();
        updateActiveDocDetails(docId);

        if (shouldRefreshList) {
            renderDocumentsList();
        }
    }

    function updateActiveDocDetails(docId) {
        const doc = state.documents.find(d => d.doc_id === docId);

        if (!doc) {
            activeDocTitle.textContent = "Select a Document";
            metaPages.textContent = "0 pages";
            metaChunks.textContent = "0 chunks";
            metaStatus.textContent = "No Document Selected";
            metaStatus.className = "status-badge status-idle";

            emptyState.hidden = false;
            docWelcomeChips.hidden = true;
            chatMessages.innerHTML = "";
            questionInput.disabled = true;
            sendBtn.disabled = true;
            return;
        }

        activeDocTitle.textContent = doc.filename;
        metaPages.textContent = `${doc.page_count || 0} pages`;
        metaChunks.textContent = `${doc.chunk_count || 0} chunks`;
        metaStatus.textContent = doc.status;
        metaStatus.className = `status-badge status-${doc.status}`;

        emptyState.hidden = true;

        if (doc.status === "ready") {
            docWelcomeChips.hidden = false;
            questionInput.disabled = false;
            sendBtn.disabled = false;
            loadChatHistory(docId);
        }
    }

    async function loadChatHistory(docId) {
        chatMessages.innerHTML = "";
        try {
            const res = await fetch(`/documents/${docId}/history`);
            if (!res.ok) return;
            const data = await res.json();
            const history = data.history || [];

            if (history.length > 0) {
                docWelcomeChips.hidden = true;
                history.forEach(turn => {
                    appendUserBubble(turn.question);
                    appendAssistantBubble(turn.answer);
                });
                scrollToBottom();
            }
        } catch (err) {
            console.error("loadChatHistory error:", err);
        }
    }

    function startStatusPolling(docId) {
        if (state.pollingIntervals[docId]) return;

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/status/${docId}`);
                if (!res.ok) return;
                const doc = await res.json();

                // Update local document record
                const idx = state.documents.findIndex(d => d.doc_id === docId);
                if (idx !== -1) {
                    state.documents[idx] = doc;
                } else {
                    state.documents.push(doc);
                }

                renderDocumentsList();

                if (state.activeDocId === docId) {
                    selectActiveDocument(docId);
                }

                // Update progress container if active upload
                if (ingestionProgress.dataset.docId === docId) {
                    progressFilename.textContent = doc.filename;
                    progressStatus.textContent = `Stage: ${doc.status}...`;
                    
                    const stagePercentMap = {
                        processing: 20,
                        parsing: 40,
                        chunking: 60,
                        embedding: 80,
                        indexing: 90,
                        ready: 100,
                        failed: 100
                    };
                    const pct = stagePercentMap[doc.status] || 50;
                    progressFill.style.width = `${pct}%`;
                    progressPercent.textContent = `${pct}%`;
                }

                if (doc.status === "ready" || doc.status === "failed") {
                    clearInterval(interval);
                    delete state.pollingIntervals[docId];

                    if (ingestionProgress.dataset.docId === docId) {
                        setTimeout(() => {
                            ingestionProgress.hidden = true;
                        }, 1200);
                    }

                    if (doc.status === "ready") {
                        showToast(`"${doc.filename}" indexed successfully!`, "success");
                        if (!state.activeDocId) selectActiveDocument(docId);
                    } else {
                        showToast(`Ingestion failed for "${doc.filename}": ${doc.error_message}`, "error");
                    }
                }
            } catch (err) {
                console.error("polling error:", err);
            }
        }, 1500);

        state.pollingIntervals[docId] = interval;
    }

    // ── 4. Upload & Drag-and-Drop ────────────────────────────────────────
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            showToast("Only PDF documents (.pdf) are allowed.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        // Show progress bar
        ingestionProgress.hidden = false;
        ingestionProgress.dataset.docId = "";
        progressFilename.textContent = file.name;
        progressStatus.textContent = "Uploading to server...";
        progressFill.style.width = "10%";
        progressPercent.textContent = "10%";

        try {
            const res = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.message || "Upload failed.");
            }

            const docId = data.doc_id;
            ingestionProgress.dataset.docId = docId;
            showToast("PDF uploaded. Ingestion running in background...", "info");

            await fetchDocuments();
            selectActiveDocument(docId);
            startStatusPolling(docId);

        } catch (err) {
            ingestionProgress.hidden = true;
            showToast(err.message, "error");
        }
    }

    // ── 5. Chat Interaction & SSE Streaming ──────────────────────────────
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitQuestion(questionInput.value);
    });

    // Sample question chips
    docWelcomeChips.addEventListener("click", (e) => {
        const chip = e.target.closest(".sample-chip");
        if (chip && chip.dataset.query) {
            submitQuestion(chip.dataset.query);
        }
    });

    async function submitQuestion(questionText) {
        const q = questionText.trim();
        if (!q || !state.activeDocId) return;

        questionInput.value = "";
        docWelcomeChips.hidden = true;

        appendUserBubble(q);
        scrollToBottom();

        // Create Assistant Bubble Container
        const assistantBubble = appendAssistantBubble("");
        assistantBubble.innerHTML = `<div class="skeleton-line" style="width: 80%;"></div><div class="skeleton-line" style="width: 60%;"></div>`;
        
        questionInput.disabled = true;
        sendBtn.disabled = true;

        try {
            const response = await fetch("/ask/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    doc_id: state.activeDocId,
                    question: q
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to initiate stream.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let fullText = "";
            let sources = [];
            assistantBubble.innerHTML = ""; // Clear skeleton loader

            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop() || ""; // Keep incomplete trailing fragment in buffer

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.replace(/^data:\s*/, "").trim();
                        if (!jsonStr) continue;

                        try {
                            const payload = JSON.parse(jsonStr);

                            if (payload.token) {
                                fullText += payload.token;
                                assistantBubble.innerHTML = formatMarkdownText(fullText);
                                scrollToBottom();
                            }

                            if (payload.done) {
                                sources = payload.sources || [];
                            }

                            if (payload.error) {
                                assistantBubble.innerHTML += `<br><span style="color: var(--status-failed-text);">⚠️ ${escapeHtml(payload.error)}</span>`;
                            }
                        } catch (e) {
                            console.error("SSE parse error:", e, jsonStr);
                        }
                    }
                }
            }

            // Render Sources Section if available
            if (sources.length > 0) {
                renderSourcesSection(assistantBubble, sources);
            }

        } catch (err) {
            assistantBubble.innerHTML = `<span style="color: var(--status-failed-text);">Error: ${escapeHtml(err.message)}</span>`;
            showToast(err.message, "error");
        } finally {
            questionInput.disabled = false;
            sendBtn.disabled = false;
            questionInput.focus();
        }
    }

    function appendUserBubble(text) {
        const turnDiv = document.createElement("div");
        turnDiv.className = "message-turn";
        
        const bubble = document.createElement("div");
        bubble.className = "user-bubble";
        bubble.textContent = text;
        
        turnDiv.appendChild(bubble);
        chatMessages.appendChild(turnDiv);
        return bubble;
    }

    function appendAssistantBubble(initialText) {
        const turnDiv = document.createElement("div");
        turnDiv.className = "message-turn";
        
        const bubble = document.createElement("div");
        bubble.className = "assistant-bubble";
        bubble.innerHTML = initialText ? formatMarkdownText(initialText) : "";
        
        turnDiv.appendChild(bubble);
        chatMessages.appendChild(turnDiv);
        return bubble;
    }

    function renderSourcesSection(assistantBubble, sources) {
        const container = document.createElement("div");
        container.className = "sources-container";

        const toggle = document.createElement("div");
        toggle.className = "sources-toggle";
        toggle.innerHTML = `📚 Verified Sources (${sources.length} excerpts)`;

        const chipsList = document.createElement("div");
        chipsList.className = "sources-chips-list";

        sources.forEach((src, idx) => {
            const pagesLabel = src.pages.map(p => `p. ${p}`).join(", ");
            const chip = document.createElement("button");
            chip.className = "citation-chip";
            chip.innerHTML = `Excerpts #${idx + 1} (${pagesLabel})`;
            
            chip.addEventListener("click", () => {
                openCitationDrawer(src);
            });

            chipsList.appendChild(chip);
        });

        container.appendChild(toggle);
        container.appendChild(chipsList);
        assistantBubble.appendChild(container);
    }

    // ── 6. Citation Side Drawer ──────────────────────────────────────────
    function openCitationDrawer(source) {
        drawerPages.textContent = `Page ${source.pages.join(", ")}`;
        drawerScore.textContent = `Similarity Score: ${source.score}`;
        drawerContent.textContent = source.text;
        
        citationDrawer.hidden = false;
        drawerBackdrop.hidden = false;
        setTimeout(() => citationDrawer.classList.add("open"), 10);
    }

    function closeCitationDrawer() {
        citationDrawer.classList.remove("open");
        setTimeout(() => {
            citationDrawer.hidden = true;
            drawerBackdrop.hidden = true;
        }, 300);
    }

    closeDrawerBtn.addEventListener("click", closeCitationDrawer);
    drawerBackdrop.addEventListener("click", closeCitationDrawer);

    // ── Helper Utilities ─────────────────────────────────────────────────
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function formatMarkdownText(text) {
        if (!text) return "";
        const lines = text.split("\n");
        const htmlLines = lines.map(line => {
            const escaped = escapeHtml(line);
            // Headings
            if (/^###\s+(.*)/.test(escaped)) {
                return escaped.replace(/^###\s+(.*)/, "<h4 style='margin: 12px 0 4px 0; font-size: 0.95rem; color: var(--text-primary); font-weight: 600;'>$1</h4>");
            }
            if (/^##\s+(.*)/.test(escaped)) {
                return escaped.replace(/^##\s+(.*)/, "<h3 style='margin: 14px 0 6px 0; font-size: 1.05rem; color: var(--text-primary); font-weight: 600;'>$1</h3>");
            }
            if (/^#\s+(.*)/.test(escaped)) {
                return escaped.replace(/^#\s+(.*)/, "<h2 style='margin: 16px 0 8px 0; font-size: 1.15rem; color: var(--text-primary); font-weight: 700;'>$1</h2>");
            }
            // Bullet points (* or -)
            if (/^\s*[\*\-]\s+(.*)/.test(escaped)) {
                return escaped.replace(/^\s*[\*\-]\s+(.*)/, "<div style='margin-left: 14px; margin-bottom: 3px; display: flex; align-items: baseline;'><span style='margin-right: 8px; color: var(--brand-primary); font-weight: bold;'>•</span><span>$1</span></div>");
            }
            return escaped;
        });

        let formatted = htmlLines.join("\n");

        // Bold **text**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Inline code `code`
        formatted = formatted.replace(/`(.*?)`/g, "<code style='background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.85em;'>$1</code>");

        // Page reference tags [Page X] or [p. X]
        formatted = formatted.replace(/\[(Page\s*\d+|p\.\s*\d+)\]/gi, "<span class='citation-chip' style='padding: 2px 6px; font-size: 0.72rem; display: inline-block; vertical-align: middle; margin: 0 2px;'>$1</span>");

        // Line breaks
        formatted = formatted.replace(/\n\n/g, "<div style='margin-bottom: 8px;'></div>").replace(/\n/g, "<br>");
        return `<div style='line-height: 1.6; color: var(--text-secondary);'>${formatted}</div>`;
    }

    // ── Initial Load ─────────────────────────────────────────────────────
    fetchDocuments();
});
