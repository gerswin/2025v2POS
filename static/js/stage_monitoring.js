/**
 * Stage Monitoring JavaScript
 * Handles real-time stage transition monitoring and price updates during purchase sessions
 */

class StageMonitor {
    constructor(eventId, options = {}) {
        this.eventId = eventId;
        this.options = {
            checkInterval: options.checkInterval || 30000, // 30 seconds
            notificationDuration: options.notificationDuration || 5000, // 5 seconds
            enableNotifications: options.enableNotifications !== false,
            enablePriceUpdates: options.enablePriceUpdates !== false,
            ...options
        };
        
        this.isMonitoring = false;
        this.monitoringInterval = null;
        this.lastKnownStages = {};
        this.callbacks = {
            onTransition: [],
            onPriceUpdate: [],
            onError: []
        };
        
        this.init();
    }
    
    init() {
        console.log('🎯 Stage Monitor initialized for event:', this.eventId);
        
        // Bind methods to preserve context
        this.checkTransitions = this.checkTransitions.bind(this);
        this.handleTransitions = this.handleTransitions.bind(this);
        this.cleanup = this.cleanup.bind(this);
        
        // Setup cleanup on page unload
        window.addEventListener('beforeunload', this.cleanup);
        window.addEventListener('pagehide', this.cleanup);
    }
    
    /**
     * Start monitoring stage transitions
     */
    start() {
        if (this.isMonitoring) {
            console.log('⚠️ Stage monitoring already active');
            return;
        }
        
        console.log('▶️ Starting stage monitoring...');
        this.isMonitoring = true;
        
        // Initial check
        this.checkTransitions();
        
        // Set up interval
        this.monitoringInterval = setInterval(
            this.checkTransitions, 
            this.options.checkInterval
        );
    }
    
    /**
     * Stop monitoring stage transitions
     */
    stop() {
        if (!this.isMonitoring) {
            return;
        }
        
        console.log('⏹️ Stopping stage monitoring...');
        this.isMonitoring = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
    }
    
    /**
     * Check for stage transitions
     */
    async checkTransitions() {
        if (!this.isMonitoring) {
            return;
        }
        
        try {
            console.log('🔄 Checking stage transitions...');
            
            const response = await fetch(
                `/api/v1/sales/check-stage-transitions/?event_id=${this.eventId}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.transitions_occurred) {
                console.log('⚡ Stage transitions detected:', data);
                this.handleTransitions(data);
            } else {
                console.log('✅ No stage transitions detected');
            }
            
        } catch (error) {
            console.error('❌ Error checking stage transitions:', error);
            this.triggerCallback('onError', error);
        }
    }
    
    /**
     * Handle detected stage transitions
     */
    handleTransitions(transitionData) {
        const transitionCount = transitionData.transitions_count || 0;
        
        // Show notification
        if (this.options.enableNotifications) {
            this.showTransitionNotification(transitionData);
        }
        
        // Update pricing displays
        if (this.options.enablePriceUpdates && transitionData.pricing_updates) {
            this.updatePricingDisplays(transitionData.pricing_updates);
        }
        
        // Trigger callbacks
        this.triggerCallback('onTransition', transitionData);
        
        // Refresh active modals if needed
        this.refreshActiveModals();
        
        // Update cart if cart update function exists
        if (typeof window.updateCartDisplay === 'function') {
            window.updateCartDisplay();
        }
    }
    
    /**
     * Show transition notification
     */
    showTransitionNotification(transitionData) {
        const transitionCount = transitionData.transitions_count || 0;
        const transitions = transitionData.transitions || [];
        
        let message = `Price stage updated! ${transitionCount} transition(s) occurred.`;
        
        if (transitions.length > 0) {
            const transitionNames = transitions.map(t => 
                `${t.from_stage} → ${t.to_stage}`
            ).join(', ');
            message += ` Transitions: ${transitionNames}`;
        }
        
        message += ' Prices may have changed.';
        
        this.showMessage(message, 'warning');
    }
    
    /**
     * Update pricing displays with new stage information
     */
    updatePricingDisplays(pricingUpdates) {
        console.log('💰 Updating pricing displays:', pricingUpdates);
        
        Object.keys(pricingUpdates).forEach(zoneId => {
            const stageInfo = pricingUpdates[zoneId];
            
            // Update zone cards
            this.updateZoneCards(zoneId, stageInfo);
            
            // Update map zones
            this.updateMapZones(zoneId, stageInfo);
            
            // Update any other pricing displays
            this.updateOtherPricingDisplays(zoneId, stageInfo);
        });
        
        // Trigger price update callbacks
        this.triggerCallback('onPriceUpdate', pricingUpdates);
    }
    
    /**
     * Update zone cards with new stage information
     */
    updateZoneCards(zoneId, stageInfo) {
        const zoneCards = document.querySelectorAll(`[data-zone-id="${zoneId}"]`);
        
        zoneCards.forEach(card => {
            if (!stageInfo.has_active_stage) {
                // Remove stage badges if no active stage
                const stageBadges = card.querySelectorAll('.stage-badge');
                stageBadges.forEach(badge => badge.remove());
                return;
            }
            
            const stage = stageInfo.stage;
            
            // Find or create stage badge
            let stageBadge = card.querySelector('.stage-badge');
            if (!stageBadge) {
                stageBadge = document.createElement('span');
                stageBadge.className = 'badge stage-badge';
                
                // Try to insert after zone price or at the end
                const zonePrice = card.querySelector('.zone-price');
                const insertTarget = zonePrice?.parentNode || card.querySelector('.card-body');
                
                if (insertTarget) {
                    insertTarget.appendChild(stageBadge);
                }
            }
            
            // Update badge content and style
            stageBadge.textContent = stage.name;
            
            // Update badge color based on modifier
            stageBadge.className = 'badge stage-badge ' + this.getStageColorClass(stage);
        });
    }
    
    /**
     * Update map zones with new stage information
     */
    updateMapZones(zoneId, stageInfo) {
        const mapZones = document.querySelectorAll(`.map-zone[data-zone-id="${zoneId}"]`);
        
        mapZones.forEach(mapZone => {
            const zoneInfo = mapZone.querySelector('.zone-info');
            if (!zoneInfo) return;
            
            // Remove existing stage info
            const existingStage = zoneInfo.querySelector('.stage-info');
            if (existingStage) {
                existingStage.remove();
            }
            
            if (!stageInfo.has_active_stage) return;
            
            const stage = stageInfo.stage;
            
            // Add new stage info
            const stageDiv = document.createElement('div');
            stageDiv.className = 'stage-info';
            stageDiv.style.fontSize = '9px';
            stageDiv.style.fontWeight = 'bold';
            stageDiv.style.color = this.getStageTextColor(stage);
            stageDiv.textContent = stage.name;
            
            zoneInfo.appendChild(stageDiv);
        });
    }
    
    /**
     * Update other pricing displays (seats, etc.)
     */
    updateOtherPricingDisplays(zoneId, stageInfo) {
        // Update seat prices if in seat selection modal
        const seatElements = document.querySelectorAll(`.seat[data-zone-id="${zoneId}"]`);
        
        seatElements.forEach(seat => {
            // Add visual indicator that prices may have changed
            seat.classList.add('price-updated');
            
            // Remove the indicator after a short delay
            setTimeout(() => {
                seat.classList.remove('price-updated');
            }, 2000);
        });
    }
    
    /**
     * Refresh active modals with updated content
     */
    refreshActiveModals() {
        const modal = document.getElementById('zoneModal');
        if (modal && modal.classList.contains('show')) {
            const modalBody = document.getElementById('zoneModalBody');
            const zoneId = modalBody?.getAttribute('data-zone-id');
            
            if (zoneId && typeof window.selectZone === 'function') {
                console.log('🔄 Refreshing modal content due to stage transition');
                
                // Show loading indicator
                this.showModalRefreshIndicator();
                
                // Reload zone content
                setTimeout(() => {
                    window.selectZone(zoneId, 'numbered');
                }, 1000);
            }
        }
    }
    
    /**
     * Show modal refresh indicator
     */
    showModalRefreshIndicator() {
        const modalBody = document.getElementById('zoneModalBody');
        if (!modalBody) return;
        
        // Add a temporary refresh indicator
        const indicator = document.createElement('div');
        indicator.className = 'alert alert-info refresh-indicator';
        indicator.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span>Updating prices due to stage transition...</span>
            </div>
        `;
        
        modalBody.insertBefore(indicator, modalBody.firstChild);
        
        // Remove indicator after 3 seconds
        setTimeout(() => {
            const existingIndicator = modalBody.querySelector('.refresh-indicator');
            if (existingIndicator) {
                existingIndicator.remove();
            }
        }, 3000);
    }
    
    /**
     * Get CSS class for stage badge based on modifier
     */
    getStageColorClass(stage) {
        const modifier = parseFloat(stage.modifier_value) || 0;
        
        if (modifier > 0) {
            return 'bg-warning'; // Price increase
        } else if (modifier < 0) {
            return 'bg-success'; // Discount
        } else {
            return 'bg-info'; // No change
        }
    }
    
    /**
     * Get text color for stage info based on modifier
     */
    getStageTextColor(stage) {
        const modifier = parseFloat(stage.modifier_value) || 0;
        
        if (modifier > 0) {
            return '#ffc107'; // Warning yellow
        } else if (modifier < 0) {
            return '#28a745'; // Success green
        } else {
            return '#17a2b8'; // Info blue
        }
    }
    
    /**
     * Show message notification
     */
    showMessage(message, type = 'info') {
        // Try to use existing showMessage function if available
        if (typeof window.showMessage === 'function') {
            window.showMessage(message, type);
            return;
        }
        
        // Fallback: create simple notification
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-triangle' : 
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle';
        
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show stage-notification" role="alert">
                <i class="bi bi-${icon}"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Insert at the top of the main content
        const content = document.querySelector('.main-content') || document.body;
        content.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-hide after duration
        setTimeout(() => {
            const alert = content.querySelector('.stage-notification');
            if (alert && typeof bootstrap !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else if (alert) {
                alert.remove();
            }
        }, this.options.notificationDuration);
    }
    
    /**
     * Add event listener for stage events
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }
    
    /**
     * Remove event listener
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            const index = this.callbacks[event].indexOf(callback);
            if (index > -1) {
                this.callbacks[event].splice(index, 1);
            }
        }
    }
    
    /**
     * Trigger callbacks for an event
     */
    triggerCallback(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${event} callback:`, error);
                }
            });
        }
    }
    
    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('🧹 Cleaning up stage monitor...');
        this.stop();
        
        // Remove event listeners
        window.removeEventListener('beforeunload', this.cleanup);
        window.removeEventListener('pagehide', this.cleanup);
        
        // Clear callbacks
        this.callbacks = {
            onTransition: [],
            onPriceUpdate: [],
            onError: []
        };
    }
    
    /**
     * Get current monitoring status
     */
    getStatus() {
        return {
            isMonitoring: this.isMonitoring,
            eventId: this.eventId,
            checkInterval: this.options.checkInterval,
            lastKnownStages: { ...this.lastKnownStages }
        };
    }
}

// Export for use in other scripts
window.StageMonitor = StageMonitor;

// Auto-initialize if event ID is available
document.addEventListener('DOMContentLoaded', function() {
    // Look for event ID in various places
    const eventId = window.currentEventId || 
                   document.body.getAttribute('data-event-id') ||
                   document.querySelector('[data-event-id]')?.getAttribute('data-event-id');
    
    if (eventId) {
        console.log('🎯 Auto-initializing stage monitor for event:', eventId);
        window.stageMonitor = new StageMonitor(eventId);
        window.stageMonitor.start();
    }
});