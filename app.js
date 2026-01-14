// ================================================
// RAIYA — FRONTEND APPLICATION HELPER SCRIPTS
// ================================================

// API CONFIGURATION
const API_BASE = '/api'; // Update with your backend URL

// ================================================
// ALERT UTILITIES
// ================================================

function showAlert(message, type = 'info', duration = 5000) {
    const alertsContainer = document.getElementById('alerts') || createAlertsContainer();
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div class="alert alert-${type}" id="${alertId}">
            <span>${message}</span>
            <button class="alert-close" onclick="document.getElementById('${alertId}').remove()">×</button>
        </div>
    `;
    
    alertsContainer.insertAdjacentHTML('beforeend', alertHTML);
    
    if (duration) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) alert.remove();
        }, duration);
    }
}

function createAlertsContainer() {
    const container = document.createElement('div');
    container.id = 'alerts';
    document.body.insertBefore(container, document.body.firstChild);
    return container;
}

// ================================================
// LOCAL STORAGE UTILITIES
// ================================================

const Storage = {
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Storage error:', error);
            return false;
        }
    },

    get: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Storage error:', error);
            return defaultValue;
        }
    },

    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Storage error:', error);
            return false;
        }
    },

    clear: () => {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Storage error:', error);
            return false;
        }
    }
};

// ================================================
// API UTILITIES
// ================================================

const API = {
    async post(endpoint, data = {}) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    },

    async get(endpoint) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    },

    async upload(endpoint, formData) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }
};

// ================================================
// FILE UTILITIES
// ================================================

const FileUtils = {
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },

    formatDate(date) {
        const d = new Date(date);
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const year = d.getFullYear();
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        return `${month}/${day}/${year} ${hours}:${minutes}`;
    },

    isPDF(file) {
        return file.type === 'application/pdf' || file.name.endsWith('.pdf');
    }
};

// ================================================
// VALIDATION UTILITIES
// ================================================

const Validation = {
    email(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    minLength(value, length) {
        return value && value.length >= length;
    },

    maxLength(value, length) {
        return !value || value.length <= length;
    },

    required(value) {
        return value && value.trim() !== '';
    },

    fileSize(file, maxMB) {
        const maxBytes = maxMB * 1024 * 1024;
        return file.size <= maxBytes;
    }
};

// ================================================
// DOM UTILITIES
// ================================================

const DOM = {
    query(selector) {
        return document.querySelector(selector);
    },

    queryAll(selector) {
        return document.querySelectorAll(selector);
    },

    create(tag, options = {}) {
        const element = document.createElement(tag);
        if (options.class) element.className = options.class;
        if (options.id) element.id = options.id;
        if (options.text) element.textContent = options.text;
        if (options.html) element.innerHTML = options.html;
        return element;
    },

    addClass(element, className) {
        element.classList.add(className);
    },

    removeClass(element, className) {
        element.classList.remove(className);
    },

    toggleClass(element, className) {
        element.classList.toggle(className);
    },

    hasClass(element, className) {
        return element.classList.contains(className);
    },

    hide(element) {
        element.style.display = 'none';
    },

    show(element, display = 'block') {
        element.style.display = display;
    },

    toggle(element) {
        element.style.display = element.style.display === 'none' ? 'block' : 'none';
    }
};

// ================================================
// FORMAT UTILITIES
// ================================================

const Format = {
    percentage(value) {
        return Math.round(value) + '%';
    },

    score(value) {
        return Math.round(value);
    },

    currency(value, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(value);
    }
};

// ================================================
// PROMISE UTILITIES
// ================================================

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ================================================
// PROGRESS TRACKING
// ================================================

class ProgressTracker {
    constructor(element, steps) {
        this.element = element;
        this.steps = steps;
        this.currentStep = 0;
    }

    update(step) {
        this.currentStep = step;
        const progress = (this.currentStep / this.steps) * 100;
        this.element.style.width = progress + '%';
    }

    complete() {
        this.element.style.width = '100%';
    }
}

// ================================================
// MODAL UTILITIES
// ================================================

class Modal {
    constructor(id) {
        this.overlay = document.getElementById(id);
        this.modal = this.overlay.querySelector('.modal');
        this.closeBtn = this.overlay.querySelector('.modal-close');
        
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }
        
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });
    }

    open() {
        this.overlay.classList.add('active');
    }

    close() {
        this.overlay.classList.remove('active');
    }

    toggle() {
        this.overlay.classList.toggle('active');
    }
}

// ================================================
// FORM UTILITIES
// ================================================

class FormHandler {
    constructor(formId) {
        this.form = document.getElementById(formId);
        this.errors = {};
    }

    getValues() {
        const formData = new FormData(this.form);
        const values = {};
        for (let [key, value] of formData.entries()) {
            values[key] = value;
        }
        return values;
    }

    reset() {
        this.form.reset();
        this.errors = {};
    }

    addError(fieldName, message) {
        this.errors[fieldName] = message;
    }

    validate(rules) {
        this.errors = {};
        const values = this.getValues();

        for (let [fieldName, rule] of Object.entries(rules)) {
            const value = values[fieldName];

            if (rule.required && !Validation.required(value)) {
                this.addError(fieldName, 'This field is required');
                continue;
            }

            if (rule.email && !Validation.email(value)) {
                this.addError(fieldName, 'Enter a valid email');
                continue;
            }

            if (rule.minLength && !Validation.minLength(value, rule.minLength)) {
                this.addError(fieldName, `Minimum ${rule.minLength} characters required`);
                continue;
            }

            if (rule.maxLength && !Validation.maxLength(value, rule.maxLength)) {
                this.addError(fieldName, `Maximum ${rule.maxLength} characters allowed`);
                continue;
            }
        }

        return Object.keys(this.errors).length === 0;
    }

    displayErrors() {
        for (let [fieldName, message] of Object.entries(this.errors)) {
            const field = this.form.elements[fieldName];
            if (field) {
                field.style.borderColor = 'var(--danger)';
                field.setAttribute('title', message);
            }
        }
    }
}

// ================================================
// INITIALIZATION
// ================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize tooltips if present
    initializeTooltips();
    
    // Setup error boundaries
    setupErrorBoundary();
});

function initializeTooltips() {
    // Implement tooltip initialization if needed
}

function setupErrorBoundary() {
    window.addEventListener('error', (event) => {
        console.error('Global error:', event.error);
        // Optionally show user-friendly error message
    });

    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        // Optionally show user-friendly error message
    });
}

// ================================================
// EXPORT FOR USE
// ================================================

console.log('Raiya app.js loaded successfully');
