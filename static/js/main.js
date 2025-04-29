// LunchMate - Main JavaScript File

// Enable Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Real-time messaging functionality
    const chatContainer = document.getElementById('chat-messages');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    
    if (chatContainer && messageForm) {
        // Scroll to bottom of chat on load
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Handle form submission
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!messageInput.value.trim()) {
                return;
            }
            
            // Send message via AJAX
            const formData = new FormData(messageForm);
            const xhr = new XMLHttpRequest();
            xhr.open('POST', messageForm.action, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    
                    // Create new message element
                    const messageElement = document.createElement('div');
                    messageElement.className = 'message message-sent';
                    messageElement.setAttribute('data-id', response.id);
                    
                    const messageContent = document.createElement('div');
                    messageContent.className = 'message-content';
                    messageContent.textContent = response.content;
                    
                    const messageTime = document.createElement('div');
                    messageTime.className = 'message-time small text-white-50';
                    messageTime.textContent = formatTime(response.created_at);
                    
                    messageElement.appendChild(messageContent);
                    messageElement.appendChild(messageTime);
                    chatContainer.appendChild(messageElement);
                    
                    // Clear input and scroll to bottom
                    messageInput.value = '';
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    
                    // Start polling for new messages
                    if (!window.isPolling) {
                        startPolling();
                    }
                }
            };
            
            xhr.send(formData);
        });
        
        // Function to start polling for new messages
        function startPolling() {
            window.isPolling = true;
            
            // Get the user ID and last message ID
            const userId = chatContainer.getAttribute('data-user-id');
            let lastId = 0;
            
            const messages = chatContainer.querySelectorAll('.message');
            if (messages.length > 0) {
                lastId = messages[messages.length - 1].getAttribute('data-id');
            }
            
            // Poll every 3 seconds
            window.pollingInterval = setInterval(function() {
                const xhr = new XMLHttpRequest();
                xhr.open('GET', `/messaging/api/messages/${userId}/poll?last_id=${lastId}`, true);
                
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        const messages = JSON.parse(xhr.responseText);
                        
                        if (messages.length > 0) {
                            // Update last ID
                            lastId = messages[messages.length - 1].id;
                            
                            // Add messages to the chat
                            messages.forEach(function(message) {
                                const messageElement = document.createElement('div');
                                messageElement.className = 'message message-received';
                                messageElement.setAttribute('data-id', message.id);
                                
                                const messageContent = document.createElement('div');
                                messageContent.className = 'message-content';
                                messageContent.textContent = message.content;
                                
                                const messageTime = document.createElement('div');
                                messageTime.className = 'message-time small text-muted';
                                messageTime.textContent = formatTime(message.created_at);
                                
                                messageElement.appendChild(messageContent);
                                messageElement.appendChild(messageTime);
                                chatContainer.appendChild(messageElement);
                            });
                            
                            // Scroll to bottom
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    }
                };
                
                xhr.send();
            }, 3000);
        }
        
        // Format timestamp
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            return `${hours}:${minutes}`;
        }
        
        // Start polling if in a conversation
        if (chatContainer.getAttribute('data-user-id')) {
            startPolling();
        }
        
        // Stop polling when leaving the page
        window.addEventListener('beforeunload', function() {
            if (window.pollingInterval) {
                clearInterval(window.pollingInterval);
            }
        });
    }
    
    // Handle file input changes for photo upload
    const photoInput = document.getElementById('photo');
    const photoPreview = document.getElementById('photo-preview');
    
    if (photoInput && photoPreview) {
        photoInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    photoPreview.src = e.target.result;
                    photoPreview.style.display = 'block';
                };
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
});

// Form validation enhancement
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    let isValid = true;
    const inputs = form.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        if (input.hasAttribute('required') && !input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Auto-scroll to bottom of message container
function scrollToBottom(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollTop = element.scrollHeight;
    }
}

// For message pages - scroll to bottom when page loads
if (document.getElementById('message-container')) {
    scrollToBottom('message-container');
}

// Image preview before upload
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (!preview) return;
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        }
        
        reader.readAsDataURL(input.files[0]);
    }
}

// Add event listeners for any file inputs that should show previews
document.addEventListener('DOMContentLoaded', function() {
    const photoInput = document.querySelector('input[type="file"][name="photo"]');
    if (photoInput && document.getElementById('photo-preview')) {
        photoInput.addEventListener('change', function() {
            previewImage(this, 'photo-preview');
        });
    }
}); 