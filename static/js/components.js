/**
 * ====================================
 * COMPONENTS.JS - TiquemaxPOS
 * Sistema de componentes JavaScript reutilizables
 * ====================================
 */

/* ====================================
   1. SISTEMA DE NOTIFICACIONES TOAST
   ==================================== */

class NotificationSystem {
  constructor() {
    this.container = this.createContainer();
    this.notifications = [];
  }

  createContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  getIcon(type) {
    const icons = {
      success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>`,
      error: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
              </svg>`,
      warning: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>`,
      info: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
               <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
             </svg>`
    };
    return icons[type] || icons.info;
  }

  show(message, type = 'info', duration = 3000) {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const toast = document.createElement('div');
    toast.id = id;
    toast.className = `toast-notification toast-${type} animate-slide-down`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    toast.innerHTML = `
      <div class="toast-icon">${this.getIcon(type)}</div>
      <div class="toast-content">
        <p class="toast-message">${message}</p>
      </div>
      <button class="toast-close" aria-label="Cerrar notificación">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
        </svg>
      </button>
    `;

    this.container.appendChild(toast);
    this.notifications.push({ id, toast, timeout: null });

    // Animación de entrada
    requestAnimationFrame(() => {
      toast.classList.add('toast-show');
    });

    // Cerrar al hacer click en el botón
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => this.hide(id));

    // Auto-cerrar si se especifica duración
    if (duration > 0) {
      const notification = this.notifications.find(n => n.id === id);
      notification.timeout = setTimeout(() => this.hide(id), duration);
    }

    return id;
  }

  hide(id) {
    const notification = this.notifications.find(n => n.id === id);
    if (!notification) return;

    const { toast, timeout } = notification;

    if (timeout) clearTimeout(timeout);

    toast.classList.add('toast-hide');
    toast.addEventListener('animationend', () => {
      toast.remove();
      this.notifications = this.notifications.filter(n => n.id !== id);
    }, { once: true });
  }

  hideAll() {
    this.notifications.forEach(({ id }) => this.hide(id));
  }

  success(message, duration) {
    return this.show(message, 'success', duration);
  }

  error(message, duration) {
    return this.show(message, 'error', duration);
  }

  warning(message, duration) {
    return this.show(message, 'warning', duration);
  }

  info(message, duration) {
    return this.show(message, 'info', duration);
  }
}

// Instancia global
const notifications = new NotificationSystem();

/* ====================================
   2. SISTEMA DE MODALES
   ==================================== */

class ModalManager {
  constructor() {
    this.activeModals = [];
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Cerrar modal al presionar ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.activeModals.length > 0) {
        const lastModal = this.activeModals[this.activeModals.length - 1];
        this.close(lastModal);
      }
    });
  }

  open(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) {
      console.error(`Modal con ID "${modalId}" no encontrado`);
      return;
    }

    // Prevenir scroll del body
    document.body.style.overflow = 'hidden';

    // Mostrar modal con animación
    modal.classList.add('modal-active');
    modal.setAttribute('aria-hidden', 'false');

    // Enfocar el primer elemento focuseable
    const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable) focusable.focus();

    this.activeModals.push(modalId);

    // Cerrar al hacer click en el backdrop
    const backdrop = modal.querySelector('.modal-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', () => this.close(modalId), { once: true });
    }
  }

  close(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('modal-closing');
    modal.setAttribute('aria-hidden', 'true');

    modal.addEventListener('animationend', () => {
      modal.classList.remove('modal-active', 'modal-closing');
      this.activeModals = this.activeModals.filter(id => id !== modalId);

      // Restaurar scroll si no hay más modales
      if (this.activeModals.length === 0) {
        document.body.style.overflow = '';
      }
    }, { once: true });
  }

  closeAll() {
    this.activeModals.forEach(modalId => this.close(modalId));
  }
}

// Instancia global
const modals = new ModalManager();

/* ====================================
   3. VALIDACIÓN DE FORMULARIOS
   ==================================== */

class FormValidator {
  constructor(formElement, rules = {}) {
    this.form = formElement;
    this.rules = rules;
    this.errors = {};
    this.setupValidation();
  }

  setupValidation() {
    // Validar en tiempo real
    this.form.querySelectorAll('input, select, textarea').forEach(field => {
      field.addEventListener('blur', () => this.validateField(field));
      field.addEventListener('input', () => {
        if (this.errors[field.name]) {
          this.validateField(field);
        }
      });
    });

    // Validar al enviar
    this.form.addEventListener('submit', (e) => {
      if (!this.validateForm()) {
        e.preventDefault();
        this.showErrors();
      }
    });
  }

  validateField(field) {
    const name = field.name;
    const value = field.value.trim();
    const rules = this.rules[name];

    if (!rules) return true;

    delete this.errors[name];

    // Required
    if (rules.required && !value) {
      this.errors[name] = rules.messages?.required || 'Este campo es requerido';
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    // Email
    if (rules.email && value && !this.isValidEmail(value)) {
      this.errors[name] = rules.messages?.email || 'Ingrese un email válido';
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    // Min length
    if (rules.minLength && value.length < rules.minLength) {
      this.errors[name] = rules.messages?.minLength || `Mínimo ${rules.minLength} caracteres`;
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    // Max length
    if (rules.maxLength && value.length > rules.maxLength) {
      this.errors[name] = rules.messages?.maxLength || `Máximo ${rules.maxLength} caracteres`;
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    // Pattern
    if (rules.pattern && !rules.pattern.test(value)) {
      this.errors[name] = rules.messages?.pattern || 'Formato inválido';
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    // Custom validation
    if (rules.custom && !rules.custom(value, field)) {
      this.errors[name] = rules.messages?.custom || 'Validación fallida';
      this.showFieldError(field, this.errors[name]);
      return false;
    }

    this.clearFieldError(field);
    return true;
  }

  validateForm() {
    this.errors = {};
    let isValid = true;

    this.form.querySelectorAll('input, select, textarea').forEach(field => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });

    return isValid;
  }

  showFieldError(field, message) {
    field.classList.add('is-invalid');
    field.setAttribute('aria-invalid', 'true');

    let errorElement = field.parentElement.querySelector('.invalid-feedback');
    if (!errorElement) {
      errorElement = document.createElement('div');
      errorElement.className = 'invalid-feedback';
      field.parentElement.appendChild(errorElement);
    }
    errorElement.textContent = message;
    errorElement.style.display = 'block';
  }

  clearFieldError(field) {
    field.classList.remove('is-invalid');
    field.setAttribute('aria-invalid', 'false');

    const errorElement = field.parentElement.querySelector('.invalid-feedback');
    if (errorElement) {
      errorElement.style.display = 'none';
    }
  }

  showErrors() {
    const firstError = Object.keys(this.errors)[0];
    if (firstError) {
      const field = this.form.querySelector(`[name="${firstError}"]`);
      if (field) field.focus();
    }
  }

  isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  reset() {
    this.errors = {};
    this.form.querySelectorAll('.is-invalid').forEach(field => {
      this.clearFieldError(field);
    });
  }
}

/* ====================================
   4. UTILIDADES GENERALES
   ==================================== */

const Utils = {
  // Debounce para búsquedas
  debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Throttle para eventos de scroll
  throttle(func, limit = 100) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },

  // Formatear moneda
  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('es-VE', {
      style: 'currency',
      currency: currency
    }).format(amount);
  },

  // Formatear fecha
  formatDate(date, options = {}) {
    const defaultOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    };
    return new Intl.DateFormat('es-VE', { ...defaultOptions, ...options }).format(new Date(date));
  },

  // Copiar al portapapeles
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      notifications.success('Copiado al portapapeles');
      return true;
    } catch (err) {
      notifications.error('Error al copiar');
      return false;
    }
  },

  // Confirmar acción
  async confirm(message, title = 'Confirmar') {
    return new Promise((resolve) => {
      // Aquí se puede implementar un modal de confirmación personalizado
      resolve(window.confirm(`${title}\n\n${message}`));
    });
  },

  // Generar ID único
  generateId(prefix = 'id') {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  // Sanitizar HTML
  sanitizeHTML(html) {
    const temp = document.createElement('div');
    temp.textContent = html;
    return temp.innerHTML;
  },

  // Scroll suave a elemento
  smoothScrollTo(element, offset = 0) {
    const targetElement = typeof element === 'string' ? document.querySelector(element) : element;
    if (!targetElement) return;

    const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - offset;
    window.scrollTo({
      top: targetPosition,
      behavior: 'smooth'
    });
  }
};

/* ====================================
   5. LOADER / SPINNER
   ==================================== */

class LoadingManager {
  constructor() {
    this.loader = this.createLoader();
    this.activeLoaders = 0;
  }

  createLoader() {
    let loader = document.getElementById('global-loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'global-loader';
      loader.className = 'loading-overlay';
      loader.innerHTML = `
        <div class="loading-spinner">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Cargando...</span>
          </div>
        </div>
      `;
      document.body.appendChild(loader);
    }
    return loader;
  }

  show() {
    this.activeLoaders++;
    this.loader.classList.add('loading-active');
    document.body.style.overflow = 'hidden';
  }

  hide() {
    this.activeLoaders = Math.max(0, this.activeLoaders - 1);
    if (this.activeLoaders === 0) {
      this.loader.classList.remove('loading-active');
      document.body.style.overflow = '';
    }
  }

  hideAll() {
    this.activeLoaders = 0;
    this.loader.classList.remove('loading-active');
    document.body.style.overflow = '';
  }
}

// Instancia global
const loading = new LoadingManager();

/* ====================================
   6. INICIALIZACIÓN AUTOMÁTICA
   ==================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-cerrar alerts de Bootstrap después de 5 segundos
  document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Tooltips de Bootstrap
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

  // Popovers de Bootstrap
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));

  console.log('TiquemaxPOS Components initialized');
});

/* ====================================
   7. EXPORTAR PARA USO GLOBAL
   ==================================== */

window.TiquemaxPOS = {
  notifications,
  modals,
  FormValidator,
  Utils,
  loading,
  version: '1.0.0'
};
