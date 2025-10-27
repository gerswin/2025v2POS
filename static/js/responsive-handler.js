/**
 * RESPONSIVE HANDLER FOR TIQUEMAX POS
 * Manages responsive interactions and mobile optimizations
 * Created: October 27, 2025
 */

(function() {
    'use strict';

    // ============================================
    // CONFIGURATION
    // ============================================

    const config = {
        breakpoints: {
            xs: 0,
            sm: 576,
            md: 768,
            lg: 992,
            xl: 1200,
            xxl: 1400
        },
        touchThreshold: 10, // pixels to determine if it's a swipe
        swipeThreshold: 100, // minimum distance for swipe
        animationDuration: 300
    };

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================

    /**
     * Get current breakpoint
     */
    function getCurrentBreakpoint() {
        const width = window.innerWidth;
        let breakpoint = 'xs';

        Object.entries(config.breakpoints).forEach(([key, value]) => {
            if (width >= value) {
                breakpoint = key;
            }
        });

        return breakpoint;
    }

    /**
     * Check if device is touch-enabled
     */
    function isTouchDevice() {
        return ('ontouchstart' in window) ||
               (navigator.maxTouchPoints > 0) ||
               (navigator.msMaxTouchPoints > 0);
    }

    /**
     * Check if device is mobile
     */
    function isMobile() {
        return window.innerWidth < config.breakpoints.md;
    }

    /**
     * Debounce function for performance
     */
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

    // ============================================
    // MOBILE NAVIGATION
    // ============================================

    class MobileNavigation {
        constructor() {
            this.sidebar = document.querySelector('.sidebar');
            this.toggleBtn = document.querySelector('.mobile-menu-toggle, #sidebarToggle');
            this.overlay = null;
            this.isOpen = false;

            if (this.sidebar && this.toggleBtn) {
                this.init();
            }
        }

        init() {
            // Create overlay
            this.createOverlay();

            // Bind events
            this.toggleBtn.addEventListener('click', () => this.toggle());

            // Close on overlay click
            if (this.overlay) {
                this.overlay.addEventListener('click', () => this.close());
            }

            // Close on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                }
            });

            // Handle swipe gestures
            this.handleSwipeGestures();
        }

        createOverlay() {
            if (!document.querySelector('.sidebar-overlay')) {
                this.overlay = document.createElement('div');
                this.overlay.className = 'sidebar-overlay';
                document.body.appendChild(this.overlay);
            } else {
                this.overlay = document.querySelector('.sidebar-overlay');
            }
        }

        toggle() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        }

        open() {
            this.sidebar.classList.add('active');
            this.overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            this.isOpen = true;

            // Announce to screen readers
            this.sidebar.setAttribute('aria-hidden', 'false');
        }

        close() {
            this.sidebar.classList.remove('active');
            this.overlay.classList.remove('active');
            document.body.style.overflow = '';
            this.isOpen = false;

            // Announce to screen readers
            this.sidebar.setAttribute('aria-hidden', 'true');
        }

        handleSwipeGestures() {
            if (!isTouchDevice()) return;

            let startX = 0;
            let startY = 0;
            let distX = 0;
            let distY = 0;

            // Swipe from left edge to open
            document.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            });

            document.addEventListener('touchmove', (e) => {
                if (!startX || !startY) return;

                distX = e.touches[0].clientX - startX;
                distY = e.touches[0].clientY - startY;

                // Horizontal swipe from left edge
                if (Math.abs(distX) > Math.abs(distY) && startX < 20 && distX > config.swipeThreshold) {
                    this.open();
                }

                // Horizontal swipe to close
                if (this.isOpen && distX < -config.swipeThreshold) {
                    this.close();
                }
            });

            document.addEventListener('touchend', () => {
                startX = 0;
                startY = 0;
            });
        }
    }

    // ============================================
    // RESPONSIVE TABLES
    // ============================================

    class ResponsiveTables {
        constructor() {
            this.tables = document.querySelectorAll('.table:not(.table-responsive-stack)');
            if (this.tables.length > 0) {
                this.init();
            }
        }

        init() {
            this.tables.forEach(table => {
                this.makeResponsive(table);
            });

            // Re-check on resize
            window.addEventListener('resize', debounce(() => {
                this.tables.forEach(table => {
                    this.updateResponsive(table);
                });
            }, 250));
        }

        makeResponsive(table) {
            // Add responsive class
            table.classList.add('table-responsive-stack');

            // Add data-label attributes to cells
            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index].textContent.trim());
                    }
                });
            });
        }

        updateResponsive(table) {
            // Update based on current viewport
            if (isMobile()) {
                table.classList.add('stacked');
            } else {
                table.classList.remove('stacked');
            }
        }
    }

    // ============================================
    // TOUCH OPTIMIZATION
    // ============================================

    class TouchOptimizer {
        constructor() {
            if (isTouchDevice()) {
                this.init();
            }
        }

        init() {
            // Add touch class to body
            document.body.classList.add('touch-device');

            // Improve button touch targets
            this.improveTouchTargets();

            // Handle fast clicks (remove 300ms delay)
            this.handleFastClicks();

            // Optimize form inputs
            this.optimizeFormInputs();
        }

        improveTouchTargets() {
            const buttons = document.querySelectorAll('.btn, button, a.nav-link');
            buttons.forEach(button => {
                const rect = button.getBoundingClientRect();
                if (rect.height < 44 || rect.width < 44) {
                    button.style.minHeight = '44px';
                    button.style.minWidth = '44px';
                }
            });
        }

        handleFastClicks() {
            // FastClick implementation for older browsers
            if ('addEventListener' in document) {
                document.addEventListener('DOMContentLoaded', () => {
                    if (typeof FastClick !== 'undefined') {
                        FastClick.attach(document.body);
                    }
                }, false);
            }
        }

        optimizeFormInputs() {
            // Add appropriate input modes
            document.querySelectorAll('input[type="tel"]').forEach(input => {
                input.setAttribute('inputmode', 'tel');
            });

            document.querySelectorAll('input[type="email"]').forEach(input => {
                input.setAttribute('inputmode', 'email');
            });

            document.querySelectorAll('input[type="number"]').forEach(input => {
                input.setAttribute('inputmode', 'decimal');
            });

            // Prevent zoom on focus (iOS)
            const metaViewport = document.querySelector('meta[name="viewport"]');
            if (metaViewport) {
                metaViewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0';
            }
        }
    }

    // ============================================
    // SEAT MAP HANDLER
    // ============================================

    class SeatMapHandler {
        constructor() {
            this.seatMap = document.querySelector('.seat-map-container');
            if (this.seatMap && isMobile()) {
                this.init();
            }
        }

        init() {
            // Enable pinch to zoom
            this.enablePinchZoom();

            // Center selected seats
            this.centerSelectedSeats();
        }

        enablePinchZoom() {
            let scale = 1;
            let initialDistance = 0;

            this.seatMap.addEventListener('touchstart', (e) => {
                if (e.touches.length === 2) {
                    initialDistance = this.getDistance(e.touches[0], e.touches[1]);
                }
            });

            this.seatMap.addEventListener('touchmove', (e) => {
                if (e.touches.length === 2) {
                    e.preventDefault();
                    const currentDistance = this.getDistance(e.touches[0], e.touches[1]);
                    scale = currentDistance / initialDistance;
                    scale = Math.min(Math.max(0.5, scale), 3); // Limit zoom
                    this.seatMap.style.transform = `scale(${scale})`;
                }
            });

            this.seatMap.addEventListener('touchend', () => {
                initialDistance = 0;
            });
        }

        getDistance(touch1, touch2) {
            const dx = touch1.clientX - touch2.clientX;
            const dy = touch1.clientY - touch2.clientY;
            return Math.sqrt(dx * dx + dy * dy);
        }

        centerSelectedSeats() {
            const selectedSeats = this.seatMap.querySelectorAll('.seat.selected');
            if (selectedSeats.length > 0) {
                selectedSeats[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'center'
                });
            }
        }
    }

    // ============================================
    // ORIENTATION HANDLER
    // ============================================

    class OrientationHandler {
        constructor() {
            this.init();
        }

        init() {
            // Initial check
            this.handleOrientationChange();

            // Listen for changes
            window.addEventListener('orientationchange', () => {
                this.handleOrientationChange();
            });

            // Fallback for devices that don't support orientationchange
            window.addEventListener('resize', debounce(() => {
                this.handleOrientationChange();
            }, 250));
        }

        handleOrientationChange() {
            const orientation = window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
            document.body.setAttribute('data-orientation', orientation);

            // Adjust specific elements for landscape
            if (orientation === 'landscape' && isMobile()) {
                this.optimizeForLandscape();
            } else {
                this.resetFromLandscape();
            }
        }

        optimizeForLandscape() {
            // Hide less important elements in landscape
            const elements = document.querySelectorAll('.hide-landscape-mobile');
            elements.forEach(el => {
                el.style.display = 'none';
            });

            // Reduce padding
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.style.paddingTop = '0.5rem';
                mainContent.style.paddingBottom = '0.5rem';
            }
        }

        resetFromLandscape() {
            const elements = document.querySelectorAll('.hide-landscape-mobile');
            elements.forEach(el => {
                el.style.display = '';
            });

            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.style.paddingTop = '';
                mainContent.style.paddingBottom = '';
            }
        }
    }

    // ============================================
    // PERFORMANCE MONITOR
    // ============================================

    class PerformanceMonitor {
        constructor() {
            if (isMobile()) {
                this.init();
            }
        }

        init() {
            // Lazy load images
            this.lazyLoadImages();

            // Optimize animations for slow devices
            this.optimizeAnimations();

            // Monitor and report performance issues
            this.monitorPerformance();
        }

        lazyLoadImages() {
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            if (img.dataset.src) {
                                img.src = img.dataset.src;
                                img.removeAttribute('data-src');
                                imageObserver.unobserve(img);
                            }
                        }
                    });
                });

                document.querySelectorAll('img[data-src]').forEach(img => {
                    imageObserver.observe(img);
                });
            }
        }

        optimizeAnimations() {
            // Check if user prefers reduced motion
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (prefersReducedMotion) {
                document.body.classList.add('reduce-motion');
            }

            // Reduce animations on low-end devices
            if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
                document.body.classList.add('low-performance');
            }
        }

        monitorPerformance() {
            if ('PerformanceObserver' in window) {
                const perfObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 1000) {
                            console.warn('Slow interaction detected:', entry.name, entry.duration);
                        }
                    }
                });

                perfObserver.observe({ entryTypes: ['measure', 'navigation'] });
            }
        }
    }

    // ============================================
    // INITIALIZATION
    // ============================================

    class ResponsiveHandler {
        constructor() {
            this.modules = {};
            this.init();
        }

        init() {
            // Wait for DOM ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.initModules());
            } else {
                this.initModules();
            }

            // Handle viewport changes
            this.handleViewportChanges();

            // Add responsive info to body
            this.updateBodyClasses();
        }

        initModules() {
            // Initialize all modules
            this.modules.navigation = new MobileNavigation();
            this.modules.tables = new ResponsiveTables();
            this.modules.touch = new TouchOptimizer();
            this.modules.seatMap = new SeatMapHandler();
            this.modules.orientation = new OrientationHandler();
            this.modules.performance = new PerformanceMonitor();

            console.log('Responsive handler initialized');
        }

        handleViewportChanges() {
            let previousBreakpoint = getCurrentBreakpoint();

            window.addEventListener('resize', debounce(() => {
                const currentBreakpoint = getCurrentBreakpoint();

                if (currentBreakpoint !== previousBreakpoint) {
                    this.onBreakpointChange(previousBreakpoint, currentBreakpoint);
                    previousBreakpoint = currentBreakpoint;
                }

                this.updateBodyClasses();
            }, 250));
        }

        onBreakpointChange(from, to) {
            // Emit custom event
            const event = new CustomEvent('breakpointChange', {
                detail: { from, to }
            });
            document.dispatchEvent(event);

            console.log(`Breakpoint changed: ${from} → ${to}`);
        }

        updateBodyClasses() {
            const breakpoint = getCurrentBreakpoint();
            const isMobileDevice = isMobile();
            const isTouchEnabled = isTouchDevice();

            // Remove old classes
            document.body.className = document.body.className.replace(/\bbreakpoint-\w+\b/g, '');

            // Add new classes
            document.body.classList.add(`breakpoint-${breakpoint}`);

            if (isMobileDevice) {
                document.body.classList.add('is-mobile');
            } else {
                document.body.classList.remove('is-mobile');
            }

            if (isTouchEnabled) {
                document.body.classList.add('touch-enabled');
            } else {
                document.body.classList.remove('touch-enabled');
            }
        }
    }

    // ============================================
    // PUBLIC API
    // ============================================

    window.TiquemaxResponsive = {
        init: function() {
            return new ResponsiveHandler();
        },

        getCurrentBreakpoint: getCurrentBreakpoint,
        isMobile: isMobile,
        isTouchDevice: isTouchDevice,

        // Expose for manual triggering
        reinitialize: function() {
            if (window.responsiveHandler) {
                window.responsiveHandler.initModules();
            }
        }
    };

    // Auto-initialize
    window.responsiveHandler = window.TiquemaxResponsive.init();

})();