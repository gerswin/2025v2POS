/**
 * Ticket Validation JavaScript
 * Handles QR code validation and ticket management functionality
 */

// Global validation functions
function validateTicketAjax(ticketIdentifier, action = 'check') {
    if (!ticketIdentifier || ticketIdentifier.trim() === '') {
        showValidationResult({
            valid: false,
            error: 'Please enter a ticket number or scan QR code'
        });
        return;
    }

    // Show loading state
    showLoadingState();

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name=csrf-token]')?.getAttribute('content');

    // Prepare request data
    const requestData = {
        ticket_identifier: ticketIdentifier.trim(),
        action: action
    };

    // Make AJAX request
    fetch('/tickets/ajax/validate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingState();
        showValidationResult(data);
        
        // Clear input after successful validation
        if (data.valid && action === 'validate_use') {
            setTimeout(() => {
                const input = document.getElementById('ticket-identifier');
                if (input) {
                    input.value = '';
                    input.focus();
                }
            }, 2000);
        }
    })
    .catch(error => {
        hideLoadingState();
        console.error('Validation error:', error);
        showValidationResult({
            valid: false,
            error: 'Network error occurred. Please try again.'
        });
    });
}

function showValidationResult(result) {
    const resultContainer = document.getElementById('validation-result');
    if (!resultContainer) return;

    let html = '';
    
    if (result.valid) {
        html = `
            <div class="validation-result validation-success">
                <h4><i class="fas fa-check-circle"></i> Valid Ticket</h4>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Ticket Number:</strong> ${result.ticket_number || 'N/A'}</p>
                        <p><strong>Customer:</strong> ${result.customer_name || 'N/A'}</p>
                        <p><strong>Event:</strong> ${result.event_name || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Seat:</strong> ${result.seat_label || 'General Admission'}</p>
                        <p><strong>Status:</strong> ${result.status || 'N/A'}</p>
                        <p><strong>Usage:</strong> ${result.usage_count || 0}/${result.max_usage || 1} 
                           (${result.remaining_uses || 0} remaining)</p>
                    </div>
                </div>
                ${result.event_start ? `<p><strong>Event Date:</strong> ${formatDateTime(result.event_start)}</p>` : ''}
                ${result.venue_name ? `<p><strong>Venue:</strong> ${result.venue_name}</p>` : ''}
                <p><small class="text-muted">Validated at: ${formatDateTime(result.timestamp)}</small></p>
            </div>
        `;
    } else {
        html = `
            <div class="validation-result validation-error">
                <h4><i class="fas fa-times-circle"></i> Invalid Ticket</h4>
                <p><strong>Reason:</strong> ${result.reason || result.error || 'Unknown error'}</p>
                <p><small class="text-muted">Checked at: ${formatDateTime(result.timestamp)}</small></p>
            </div>
        `;
    }
    
    resultContainer.innerHTML = html;
    
    // Scroll to result
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Auto-hide after some time for successful validations
    if (result.valid) {
        setTimeout(() => {
            resultContainer.innerHTML = '';
        }, 10000); // Hide after 10 seconds
    }
}

function showLoadingState() {
    const resultContainer = document.getElementById('validation-result');
    if (resultContainer) {
        resultContainer.innerHTML = `
            <div class="validation-result validation-loading">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Validating ticket...</span>
                </div>
            </div>
        `;
    }
}

function hideLoadingState() {
    // Loading state will be replaced by result
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (e) {
        return dateString;
    }
}

// QR Code Scanner Integration (if available)
function initQRScanner() {
    // Check if QR scanner library is available
    if (typeof Html5QrcodeScanner !== 'undefined') {
        const scanner = new Html5QrcodeScanner(
            "qr-reader",
            { 
                fps: 10, 
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            }
        );
        
        scanner.render(onScanSuccess, onScanFailure);
        
        function onScanSuccess(decodedText, decodedResult) {
            // Set the scanned text in the input field
            const input = document.getElementById('ticket-identifier');
            if (input) {
                input.value = decodedText;
                // Auto-validate after scan
                validateTicketAjax(decodedText, 'validate_use');
            }
            
            // Stop scanning after successful scan
            scanner.clear();
        }
        
        function onScanFailure(error) {
            // Handle scan failure silently
            console.log('QR scan failed:', error);
        }
    }
}

// Barcode scanner support
function handleBarcodeInput(event) {
    const input = event.target;
    const value = input.value;
    
    // Detect if this looks like a barcode/QR scan (rapid input)
    if (value.length > 10) {
        clearTimeout(input.barcodeTimeout);
        input.barcodeTimeout = setTimeout(() => {
            // Auto-validate if it looks like a complete scan
            if (value.length > 20 && /^[A-Za-z0-9+/=]+$/.test(value)) {
                validateTicketAjax(value, 'validate_use');
            }
        }, 300);
    }
}

// Bulk validation functionality
function validateMultipleTickets() {
    const textarea = document.getElementById('bulk-tickets');
    if (!textarea) return;
    
    const tickets = textarea.value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    if (tickets.length === 0) {
        alert('Please enter ticket numbers or QR codes, one per line.');
        return;
    }
    
    if (tickets.length > 50) {
        alert('Maximum 50 tickets can be validated at once.');
        return;
    }
    
    // Show progress
    const progressContainer = document.getElementById('bulk-progress');
    if (progressContainer) {
        progressContainer.innerHTML = `
            <div class="progress mb-3">
                <div class="progress-bar" role="progressbar" style="width: 0%">0%</div>
            </div>
            <div id="bulk-results"></div>
        `;
    }
    
    // Validate tickets one by one
    let completed = 0;
    let successful = 0;
    const results = [];
    
    tickets.forEach((ticket, index) => {
        setTimeout(() => {
            validateSingleTicketForBulk(ticket, (result) => {
                completed++;
                if (result.valid) successful++;
                results.push({ ticket, result });
                
                // Update progress
                const progress = (completed / tickets.length) * 100;
                const progressBar = document.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${Math.round(progress)}%`;
                }
                
                // Show individual result
                const resultsContainer = document.getElementById('bulk-results');
                if (resultsContainer) {
                    const resultHtml = `
                        <div class="bulk-result ${result.valid ? 'text-success' : 'text-danger'}">
                            <i class="fas fa-${result.valid ? 'check' : 'times'}"></i>
                            ${ticket}: ${result.valid ? result.customer_name : result.reason}
                        </div>
                    `;
                    resultsContainer.innerHTML += resultHtml;
                }
                
                // Show summary when complete
                if (completed === tickets.length) {
                    setTimeout(() => {
                        alert(`Bulk validation complete!\nTotal: ${tickets.length}\nSuccessful: ${successful}\nFailed: ${tickets.length - successful}`);
                    }, 500);
                }
            });
        }, index * 200); // Stagger requests
    });
}

function validateSingleTicketForBulk(ticketIdentifier, callback) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    fetch('/tickets/ajax/validate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            ticket_identifier: ticketIdentifier,
            action: 'validate_use'
        })
    })
    .then(response => response.json())
    .then(callback)
    .catch(error => {
        callback({
            valid: false,
            reason: 'Network error'
        });
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for ticket validation form
    const validationForm = document.getElementById('validation-form');
    if (validationForm) {
        validationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const identifier = document.getElementById('ticket-identifier').value;
            const action = e.submitter?.value || 'check_only';
            validateTicketAjax(identifier, action);
        });
    }
    
    // Add barcode scanner support
    const ticketInput = document.getElementById('ticket-identifier');
    if (ticketInput) {
        ticketInput.addEventListener('input', handleBarcodeInput);
        
        // Focus on load
        ticketInput.focus();
    }
    
    // Initialize QR scanner if container exists
    if (document.getElementById('qr-reader')) {
        initQRScanner();
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // F1 for quick validate
        if (e.key === 'F1') {
            e.preventDefault();
            const identifier = document.getElementById('ticket-identifier')?.value;
            if (identifier) {
                validateTicketAjax(identifier, 'validate_use');
            }
        }
        
        // F2 for quick check
        if (e.key === 'F2') {
            e.preventDefault();
            const identifier = document.getElementById('ticket-identifier')?.value;
            if (identifier) {
                validateTicketAjax(identifier, 'check');
            }
        }
        
        // Escape to clear
        if (e.key === 'Escape') {
            const input = document.getElementById('ticket-identifier');
            const result = document.getElementById('validation-result');
            if (input) {
                input.value = '';
                input.focus();
            }
            if (result) {
                result.innerHTML = '';
            }
        }
    });
});

// Export functions for global use
window.validateTicketAjax = validateTicketAjax;
window.showValidationResult = showValidationResult;
window.validateMultipleTickets = validateMultipleTickets;