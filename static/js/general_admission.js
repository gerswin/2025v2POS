// General Admission JavaScript Functions
// This file contains all JavaScript functionality for the general admission template

let unitPrice = 0;
let maxQuantity = 0;
let currentQuantity = 1;
let zoneId = '';

// Initialize the general admission functionality
function initGeneralAdmission(price, capacity, zone_id) {
    unitPrice = price;
    maxQuantity = capacity;
    zoneId = zone_id;
    currentQuantity = 1;
    
    updateTotal();
    startAvailabilityPolling();
}

function increaseQuantity() {
    const quantityInput = document.getElementById('ticketQuantity');
    const currentValue = parseInt(quantityInput.value);
    
    if (currentValue < maxQuantity) {
        quantityInput.value = currentValue + 1;
        updateTotal();
    }
}

function decreaseQuantity() {
    const quantityInput = document.getElementById('ticketQuantity');
    const currentValue = parseInt(quantityInput.value);
    
    if (currentValue > 1) {
        quantityInput.value = currentValue - 1;
        updateTotal();
    }
}

function setQuantity(quantity) {
    const quantityInput = document.getElementById('ticketQuantity');
    
    if (quantity <= maxQuantity && quantity >= 1) {
        quantityInput.value = quantity;
        updateTotal();
    }
}

function updateTotal() {
    const quantityInput = document.getElementById('ticketQuantity');
    let quantity = parseInt(quantityInput.value) || 1;
    
    // Validate quantity
    if (quantity > maxQuantity) {
        quantityInput.value = maxQuantity;
        quantity = maxQuantity;
    } else if (quantity < 1) {
        quantityInput.value = 1;
        quantity = 1;
    }
    
    currentQuantity = quantity;
    const total = unitPrice * quantity;
    
    document.getElementById('summaryQuantity').textContent = quantity;
    document.getElementById('totalPrice').textContent = '$' + total.toFixed(2);
    
    // Update button state
    const addButton = document.getElementById('addToCartBtn');
    if (maxQuantity === 0) {
        addButton.disabled = true;
        addButton.innerHTML = '<i class="bi bi-x-circle"></i> Sold Out';
    } else {
        addButton.disabled = false;
        addButton.innerHTML = '<i class="bi bi-cart-plus"></i> Add to Cart';
    }
}

function addGeneralTicketsToCart() {
    if (maxQuantity === 0) {
        return;
    }
    
    const button = document.getElementById('addToCartBtn');
    const originalText = button.innerHTML;
    
    // Show loading
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';
    
    fetch('/sales/cart/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            zone_id: zoneId,
            quantity: currentQuantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset quantity
            document.getElementById('ticketQuantity').value = 1;
            updateTotal();
            
            // Update cart display in parent window
            if (window.parent && window.parent.updateCartDisplay) {
                window.parent.updateCartDisplay();
            }
            
            // Show success message
            showMessage(data.message, 'success');
            
            // Close modal after short delay
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('zoneModal'));
                if (modal) {
                    modal.hide();
                }
            }, 1000);
        } else {
            showMessage(data.error || 'Error adding tickets to cart', 'error');
        }
    })
    .catch(error => {
        showMessage('Error adding tickets to cart', 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

function startAvailabilityPolling() {
    // Update zone availability every 10 seconds
    setInterval(() => {
        fetch(`/sales/ajax/zone-availability/?zone_id=${zoneId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.availability) {
                    const availability = data.availability;
                    const newMaxQuantity = availability.available_seats;
                    
                    // Update availability display
                    const availabilityFill = document.querySelector('.availability-fill');
                    const availabilityText = document.querySelector('.availability-text');
                    
                    if (availabilityFill && availabilityText) {
                        const occupancyPercentage = availability.occupancy_percentage;
                        availabilityFill.style.width = occupancyPercentage + '%';
                        
                        availabilityText.innerHTML = `
                            <div class="row">
                                <div class="col-6">
                                    <small class="text-success">
                                        <i class="bi bi-check-circle"></i>
                                        <strong>${availability.available_seats}</strong> Available
                                    </small>
                                </div>
                                <div class="col-6 text-end">
                                    <small class="text-muted">
                                        <strong>${availability.total_seats - availability.available_seats}</strong> Sold
                                    </small>
                                </div>
                            </div>
                        `;
                    }
                    
                    // Update max quantity if it changed
                    if (newMaxQuantity !== maxQuantity) {
                        maxQuantity = newMaxQuantity;
                        const quantityInput = document.getElementById('ticketQuantity');
                        quantityInput.max = maxQuantity;
                        
                        // Adjust current quantity if it exceeds new max
                        if (parseInt(quantityInput.value) > maxQuantity) {
                            quantityInput.value = Math.max(1, maxQuantity);
                            updateTotal();
                        }
                    }
                }
            })
            .catch(error => {
                console.log('Error updating zone availability:', error);
            });
    }, 10000);
}

function showMessage(message, type) {
    // This function should be available from the parent page
    if (window.parent && window.parent.showMessage) {
        window.parent.showMessage(message, type);
    }
}

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