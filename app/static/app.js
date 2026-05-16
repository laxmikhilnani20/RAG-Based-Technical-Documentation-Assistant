const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const chatHistory = document.getElementById('chat-history');
const sendBtn = document.getElementById('send-btn');

let currentSessionId = null;

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = queryInput.value.trim();
    if (!question) return;

    // 1. Add User Message
    addUserMessage(question);
    queryInput.value = '';
    queryInput.disabled = true;
    sendBtn.disabled = true;

    // 2. Add Loading Indicator
    const loadingId = addLoadingIndicator();

    try {
        // 3. Call API
        const payload = { question: question };
        if (currentSessionId) {
            payload.session_id = currentSessionId;
        }

        const response = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'API Error');
        }

        const data = await response.json();
        
        // Save session ID for follow-ups
        if (data.session_id) {
            currentSessionId = data.session_id;
        }

        // 4. Remove Loading Indicator & Add Assistant Message
        removeElement(loadingId);
        
        // Ensure data.answer exists, fallback if necessary
        const answerText = data.answer || "I encountered an error generating an answer.";
        addAssistantMessage(answerText, data.sources, data.session_id);

    } catch (error) {
        removeElement(loadingId);
        addAssistantMessage(`**Error:** ${error.message}\n\n*Note: If you are using the free tier, you may have hit the 5 requests-per-minute limit. Please wait 60 seconds.*`, []);
    } finally {
        queryInput.disabled = false;
        sendBtn.disabled = false;
        queryInput.focus();
        scrollToBottom();
    }
});

function addUserMessage(text) {
    const msgHTML = `
        <div class="message user-message appear-anim">
            <div class="avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-content">
                <p>${text}</p>
            </div>
        </div>
    `;
    chatHistory.insertAdjacentHTML('beforeend', msgHTML);
    scrollToBottom();
}

function addAssistantMessage(text, sources, queryId) {
    // Parse markdown
    const parsedText = marked.parse(text);
    
    // Build sources HTML if available
    let sourcesHTML = '';
    if (sources && sources.length > 0) {
        const badges = sources.map(s => `
            <a href="${s.url}" target="_blank" class="source-badge" title="${s.chunk_preview.replace(/"/g, '&quot;')}">
                <i class="fa-solid fa-link"></i> ${s.document}
            </a>
        `).join('');
        
        sourcesHTML = `
            <div class="sources-container">
                <div class="sources-title">Sources</div>
                <div class="source-badges">
                    ${badges}
                </div>
            </div>
        `;
    }

    // Build Feedback HTML
    const feedbackHTML = queryId ? `
        <div class="feedback-actions">
            <button class="feedback-btn" onclick="submitFeedback(this, '${queryId}', 'up')"><i class="fa-solid fa-thumbs-up"></i></button>
            <button class="feedback-btn" onclick="submitFeedback(this, '${queryId}', 'down')"><i class="fa-solid fa-thumbs-down"></i></button>
        </div>
    ` : '';

    const msgHTML = `
        <div class="message assistant-message appear-anim">
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content">
                ${parsedText}
                ${sourcesHTML}
                ${feedbackHTML}
            </div>
        </div>
    `;
    
    chatHistory.insertAdjacentHTML('beforeend', msgHTML);
    scrollToBottom();
}

function addLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const msgHTML = `
        <div class="message assistant-message" id="${id}">
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    chatHistory.insertAdjacentHTML('beforeend', msgHTML);
    scrollToBottom();
    return id;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Global function for feedback buttons
async function submitFeedback(btnElement, queryId, rating) {
    // Visual toggle
    const container = btnElement.parentElement;
    const buttons = container.querySelectorAll('.feedback-btn');
    buttons.forEach(b => b.classList.remove('active', 'up', 'down'));
    
    btnElement.classList.add('active', rating);

    try {
        await fetch('/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query_id: queryId,
                rating: rating
            })
        });
    } catch (e) {
        console.error("Failed to submit feedback", e);
    }
}
