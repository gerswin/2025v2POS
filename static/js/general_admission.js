// General Admission JavaScript Functions
// This file contains all JavaScript functionality for the general admission template

let unitPrice = 0;
let maxQuantity = 0;
let currentQuantity = 0;
let zoneId = '';
let rawAvailableCapacity = 0;
let totalCapacity = 0;
let cartQuantity = 0;
let soldSeats = 0;
let availabilityIntervalId = null;

function toInt(value, fallback = 0) {
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
}

function toNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? fallback : parsed;
}

function stopAvailabilityPolling() {
    if (availabilityIntervalId) {
        clearInterval(availabilityIntervalId);
        availabilityIntervalId = null;
    }
}

function handleModalHidden(event) {
    if (event && event.target && event.target.id === 'zoneModal') {
        stopAvailabilityPolling();
    }
}

// Initialize the general admission functionality
function initGeneralAdmission(configOrPrice, capacity, zone_id, initialCartQty = 0) {
    stopAvailabilityPolling();

    if (typeof configOrPrice === 'object' && configOrPrice !== null) {
        const config = configOrPrice;
        unitPrice = toNumber(config.unitPrice ?? config.price, 0);
        zoneId = config.zoneId ?? '';
        rawAvailableCapacity = toInt(
            config.zoneAvailableCapacity ??
            config.availableCapacity ??
            config.availableSeats ??
            config.available
        );
        totalCapacity = toInt(
            config.totalCapacity ??
            config.zoneCapacity ??
            config.capacity ??
            (rawAvailableCapacity + toInt(config.soldCount ?? config.soldSeats ?? 0))
        );
        cartQuantity = toInt(config.cartQuantity, 0);
        soldSeats = toInt(
            config.soldCount ??
            config.soldSeats ??
            (totalCapacity - rawAvailableCapacity)
        );
        maxQuantity = Math.max(
            toInt(
                config.effectiveAvailableCapacity ??
                config.effectiveAvailableSeats ??
                (rawAvailableCapacity - cartQuantity)
            ),
            0
        );
    } else {
        unitPrice = toNumber(configOrPrice, 0);
        zoneId = zone_id || '';
        rawAvailableCapacity = toInt(capacity, 0);
        totalCapacity = rawAvailableCapacity;
        cartQuantity = toInt(initialCartQty, 0);
        soldSeats = Math.max(totalCapacity - rawAvailableCapacity, 0);
        maxQuantity = Math.max(rawAvailableCapacity - cartQuantity, 0);
    }

    if (rawAvailableCapacity < 0) {
        rawAvailableCapacity = 0;
    }

    if (totalCapacity < rawAvailableCapacity + cartQuantity) {
        totalCapacity = rawAvailableCapacity + cartQuantity;
    }

    currentQuantity = maxQuantity > 0 ? 1 : 0;

    applyGeneralAdmissionState();
    startAvailabilityPolling();

    if (!window._generalAdmissionModalCleanupAttached) {
        document.addEventListener('hidden.bs.modal', handleModalHidden, { passive: true });
        window._generalAdmissionModalCleanupAttached = true;
    }
}

function applyGeneralAdmissionState() {
    const quantityInput = document.getElementById('ticketQuantity');
    if (!quantityInput) {
        return;
    }

    const minValue = maxQuantity > 0 ? 1 : 0;
    quantityInput.min = minValue;
    quantityInput.max = maxQuantity;

    if (maxQuantity === 0) {
        currentQuantity = 0;
        quantityInput.value = 0;
    } else {
        if (currentQuantity < 1) {
            currentQuantity = 1;
        }
        if (currentQuantity > maxQuantity) {
            currentQuantity = maxQuantity;
        }
        quantityInput.value = currentQuantity;
    }

    updateAvailabilityIndicators();
    updateQuickSelectButtons();
    updateCartReservationNotice();
    updateAddToCartButton();
    updateTotal();
}

function calculateOccupancyPercentage() {
    if (totalCapacity <= 0) {
        return 0;
    }

    const sold = Math.min(
        totalCapacity,
        totalCapacity - rawAvailableCapacity
    );

    const percentage = (sold / totalCapacity) * 100;
    return Number.isNaN(percentage) ? 0 : Number(percentage.toFixed(2));
}

function updateAvailabilityIndicators() {
    const maxTicketsText = document.getElementById('maxTicketsText');
    if (maxTicketsText) {
        const template = maxTicketsText.dataset.template;
        if (template) {
            maxTicketsText.textContent = template.replace('__max__', maxQuantity);
        } else {
            maxTicketsText.textContent = `Maximum: ${maxQuantity} tickets`;
        }
    }

    const availableSeatsValue = document.getElementById('availableSeatsValue');
    if (availableSeatsValue) {
        availableSeatsValue.textContent = Math.max(rawAvailableCapacity, 0);
    }

    const soldSeatsValue = document.getElementById('soldSeatsValue');
    if (soldSeatsValue) {
        const sold = soldSeats || (totalCapacity - rawAvailableCapacity);
        soldSeatsValue.textContent = Math.max(toInt(sold, 0), 0);
    }

    const availabilityFill = document.getElementById('availabilityFill');
    if (availabilityFill) {
        const percentage = calculateOccupancyPercentage();
        availabilityFill.style.width = `${percentage}%`;
        availabilityFill.dataset.percentage = percentage;
    }
}

function updateQuickSelectButtons() {
    const quickSelectButtons = document.querySelectorAll('.quick-select .btn-group .btn');
    if (!quickSelectButtons) {
        return;
    }

    quickSelectButtons.forEach(button => {
        const value = toInt(button.textContent, 0);
        if (value > 0 && value <= maxQuantity) {
            button.disabled = false;
            button.classList.remove('disabled');
        } else {
            button.disabled = true;
            button.classList.add('disabled');
        }
    });
}

function updateCartReservationNotice() {
    const notice = document.getElementById('cartReservationNotice');
    if (!notice) {
        return;
    }

    if (cartQuantity > 0) {
        const singular = notice.dataset.messageSingular || '';
        const plural = notice.dataset.messagePlural || singular;
        const chosenMessage = cartQuantity === 1 ? singular : plural;
        notice.textContent = chosenMessage.replace('__count__', cartQuantity);
        notice.hidden = false;
    } else {
        notice.hidden = true;
    }
}

function setAddToCartButtonState(state) {
    const button = document.getElementById('addToCartBtn');
    const icon = document.getElementById('addToCartIcon');
    const text = document.getElementById('addToCartText');

    if (!button || !icon || !text) {
        return;
    }

    const iconDefault = button.dataset.iconDefault || 'bi bi-cart-plus';
    const iconSoldOut = button.dataset.iconSoldout || 'bi bi-x-circle';
    const iconLocked = button.dataset.iconLocked || 'bi bi-lock';
    const labelDefault = button.dataset.labelDefault || 'Add to Cart';
    const labelSoldOut = button.dataset.labelSoldout || 'Sold Out';
    const labelInCart = button.dataset.labelIncart || 'In Cart';

    switch (state) {
        case 'soldout':
            icon.className = iconSoldOut;
            text.textContent = labelSoldOut;
            button.disabled = true;
            break;
        case 'locked':
            icon.className = iconLocked;
            text.textContent = labelInCart;
            button.disabled = true;
            break;
        default:
            icon.className = iconDefault;
            text.textContent = labelDefault;
            button.disabled = false;
            break;
    }
}

function updateAddToCartButton() {
    if (maxQuantity === 0) {
        if (cartQuantity > 0) {
            setAddToCartButtonState('locked');
        } else {
            setAddToCartButtonState('soldout');
        }
    } else {
        setAddToCartButtonState('default');
    }
}

function increaseQuantity() {
    if (maxQuantity === 0) {
        return;
    }

    const quantityInput = document.getElementById('ticketQuantity');
    const currentValue = toInt(quantityInput.value, currentQuantity);
    
    if (currentValue < maxQuantity) {
        quantityInput.value = currentValue + 1;
        updateTotal();
    }
}

function decreaseQuantity() {
    if (maxQuantity === 0) {
        return;
    }

    const quantityInput = document.getElementById('ticketQuantity');
    const currentValue = toInt(quantityInput.value, currentQuantity);
    
    if (currentValue > 1) {
        quantityInput.value = currentValue - 1;
        updateTotal();
    }
}

function setQuantity(quantity) {
    if (maxQuantity === 0) {
        return;
    }

    const quantityInput = document.getElementById('ticketQuantity');
    
    if (quantity <= maxQuantity && quantity >= 1) {
        quantityInput.value = quantity;
        updateTotal();
    }
}

function updateTotal() {
    const quantityInput = document.getElementById('ticketQuantity');
    if (!quantityInput) {
        return;
    }

    let quantity = toInt(quantityInput.value, currentQuantity);

    if (maxQuantity === 0) {
        quantity = 0;
    } else {
        if (quantity > maxQuantity) {
            quantity = maxQuantity;
        } else if (quantity < 1) {
            quantity = 1;
        }
    }

    currentQuantity = quantity;
    quantityInput.value = quantity;

    const total = unitPrice * quantity;
    
    const summaryQuantityElement = document.getElementById('summaryQuantity');
    if (summaryQuantityElement) {
        summaryQuantityElement.textContent = quantity;
    }
    
    const totalPriceElement = document.getElementById('totalPrice');
    if (totalPriceElement) {
        totalPriceElement.textContent = '$' + total.toFixed(2);
    }
}

function addGeneralTicketsToCart() {
    if (maxQuantity === 0) {
        showMessage('No tickets available to add.', 'error');
        return;
    }

    if (currentQuantity <= 0) {
        showMessage('Select at least one ticket to add to the cart.', 'error');
        return;
    }
    
    const button = document.getElementById('addToCartBtn');
    if (!button) {
        return;
    }

    const originalContent = button.innerHTML;
    
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
            cartQuantity += currentQuantity;
            maxQuantity = Math.max(rawAvailableCapacity - cartQuantity, 0);
            currentQuantity = maxQuantity > 0 ? Math.min(currentQuantity, maxQuantity) : 0;
            applyGeneralAdmissionState();
            
            // Update cart display in parent window
            if (window.parent && window.parent.updateCartDisplay) {
                window.parent.updateCartDisplay();
            }
            
            // Show success message
            showMessage(data.message, 'success');
            
            // Close modal after short delay
            setTimeout(() => {
                const modalElement = document.getElementById('zoneModal');
                if (modalElement) {
                    const modalInstance = bootstrap.Modal.getInstance(modalElement);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                }
            }, 1000);
        } else {
            showMessage(data.error || 'Error adding tickets to cart', 'error');
        }
    })
    .catch(() => {
        showMessage('Error adding tickets to cart', 'error');
    })
    .finally(() => {
        button.innerHTML = originalContent;
        updateAddToCartButton();
    });
}

function startAvailabilityPolling() {
    if (!zoneId) {
        return;
    }

    stopAvailabilityPolling();

    const refreshAvailability = () => {
        fetch(`/sales/ajax/zone-availability/?zone_id=${zoneId}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success || !data.availability) {
                    return;
                }

                const availability = data.availability;

                rawAvailableCapacity = toInt(
                    availability.available_seats ??
                    availability.available_capacity ??
                    availability.available
                );

                totalCapacity = toInt(
                    availability.total_seats ??
                    availability.total_capacity ??
                    availability.capacity ??
                    (availability.available_seats + availability.sold_seats)
                , totalCapacity);

                cartQuantity = toInt(availability.cart_quantity, cartQuantity);

                const effectiveAvailable = toInt(
                    availability.effective_available_seats ??
                    (rawAvailableCapacity - cartQuantity),
                    0
                );

                maxQuantity = Math.max(effectiveAvailable, 0);

                soldSeats = toInt(
                    availability.sold_seats ??
                    availability.sold_capacity ??
                    (totalCapacity - rawAvailableCapacity),
                    soldSeats
                );

                applyGeneralAdmissionState();
            })
            .catch(() => {
                // Silent fail to avoid noisy console in production
            });
    };

    refreshAvailability();
    availabilityIntervalId = setInterval(refreshAvailability, 10000);
}

function showMessage(message, type) {
    // This function should be available from the parent page
    if (window.parent && window.parent.showMessage && window.parent !== window) {
        window.parent.showMessage(message, type);
    } else {
        // Fallback: simple console log or alert
        console.log(`${type.toUpperCase()}: ${message}`);
        if (type === 'error') {
            console.error(message);
        }
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

function syncGeneralAdmissionCart(cartItems) {
    if (!zoneId || !Array.isArray(cartItems)) {
        return;
    }

    const matchingItem = cartItems.find(item => {
        if (!item) {
            return false;
        }
        const itemZoneId = item.zone_id || item.zoneId;
        return itemZoneId === zoneId && item.type === 'general_admission';
    });

    cartQuantity = matchingItem ? toInt(matchingItem.quantity, 0) : 0;
    maxQuantity = Math.max(rawAvailableCapacity - cartQuantity, 0);

    // Adjust current quantity if needed
    if (currentQuantity > maxQuantity) {
        currentQuantity = maxQuantity > 0 ? maxQuantity : 0;
    }

    applyGeneralAdmissionState();
}

window.syncGeneralAdmissionCart = syncGeneralAdmissionCart;
