document.addEventListener('DOMContentLoaded', () => {
    const chatWidget = document.getElementById('ai-chat-widget');
    const chatButton = document.getElementById('ai-chat-button');
    const chatWindow = document.getElementById('ai-chat-window');
    const closeChat = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const sendChat = document.getElementById('send-chat');
    const chatMessages = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');

    // Générer un session_id unique s'il n'existe pas
    if (!localStorage.getItem('ai_session_id')) {
        localStorage.setItem('ai_session_id', 'sess_' + Math.random().toString(36).substr(2, 9));
    }
    const sessionId = localStorage.getItem('ai_session_id');

    // Toggle Chat Window
    chatButton.addEventListener('click', () => {
        chatWindow.classList.toggle('active');
        if (chatWindow.classList.contains('active')) {
            chatInput.focus();
        }
    });

    closeChat.addEventListener('click', () => {
        chatWindow.classList.remove('active');
    });

    const addMessage = (content, isUser = false) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'message-user' : 'message-ia'}`;
        msgDiv.textContent = content;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const sendMessage = async () => {
        const question = chatInput.value.strip ? chatInput.value.strip() : chatInput.value.trim();
        if (!question) return;

        addMessage(question, true);
        chatInput.value = '';
        typingIndicator.style.display = 'block';

        try {
            const response = await fetch('/ai-assistant/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    question: question,
                    session_id: sessionId
                })
            });

            const data = await response.json();
            typingIndicator.style.display = 'none';

            if (data.response) {
                addMessage(data.response);
            } else {
                addMessage("Désolé, une erreur est survenue.", false);
            }
        } catch (error) {
            typingIndicator.style.display = 'none';
            addMessage("Impossible de contacter l'assistant.", false);
            console.error('Chat error:', error);
        }
    };

    sendChat.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Helper pour récupérer le CSRF Token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
