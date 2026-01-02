/**
 * Stock Page Interactive JavaScript
 * Handles tab switching, mobile navigation, and smooth scrolling
 */

(function() {
    'use strict';

    // ===== State Management =====
    let currentSection = 'overview';
    const sections = ['overview', 'forecast', 'technical', 'fundamentals', 'company', 'trading', 'conclusion'];
    
    // ===== DOM Elements =====
    const tabButtons = document.querySelectorAll('.tab-button');
    const mobileTabOptions = document.querySelectorAll('.mobile-tab-option');
    const sectionContents = document.querySelectorAll('.section-content');
    const mobileDropdownBtn = document.getElementById('mobileSectionBtn');
    const mobileDropdownMenu = document.getElementById('mobileDropdownMenu');
    const currentSectionName = document.getElementById('currentSectionName');

    // ===== Initialize =====
    function init() {
        setupTabListeners();
        setupMobileDropdown();
        setupKeyboardNavigation();
        setupURLHash();
        
        console.log('Stock Page initialized successfully');
    }

    // ===== Tab Switching Logic =====
    function switchToSection(sectionName) {
        if (!sections.includes(sectionName)) {
            console.warn(`Invalid section: ${sectionName}`);
            return;
        }

        // Update current section
        currentSection = sectionName;

        // Hide all sections
        sectionContents.forEach(section => {
            section.classList.remove('active');
        });

        // Show selected section
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Smooth scroll to top of content
            targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Update desktop tabs
        tabButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.section === sectionName) {
                btn.classList.add('active');
            }
        });

        // Update mobile dropdown options
        mobileTabOptions.forEach(option => {
            option.classList.remove('active');
            if (option.dataset.section === sectionName) {
                option.classList.add('active');
            }
        });

        // Update mobile dropdown button text
        updateMobileDropdownText(sectionName);

        // Close mobile dropdown if open
        closeMobileDropdown();

        // Update URL hash without scrolling
        updateURLHash(sectionName);

        // Track section view (for analytics)
        trackSectionView(sectionName);
    }

    // ===== Tab Listeners =====
    function setupTabListeners() {
        // Desktop tab buttons
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionName = button.dataset.section;
                switchToSection(sectionName);
            });
        });

        // Mobile tab options
        mobileTabOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionName = option.dataset.section;
                switchToSection(sectionName);
            });
        });
    }

    // ===== Mobile Dropdown Logic =====
    function setupMobileDropdown() {
        if (!mobileDropdownBtn || !mobileDropdownMenu) return;

        mobileDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMobileDropdown();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!mobileDropdownMenu.contains(e.target) && !mobileDropdownBtn.contains(e.target)) {
                closeMobileDropdown();
            }
        });

        // Prevent dropdown from closing when clicking inside
        mobileDropdownMenu.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    function toggleMobileDropdown() {
        mobileDropdownMenu.classList.toggle('show');
        mobileDropdownBtn.classList.toggle('open');
    }

    function closeMobileDropdown() {
        mobileDropdownMenu.classList.remove('show');
        mobileDropdownBtn.classList.remove('open');
    }

    function updateMobileDropdownText(sectionName) {
        if (!currentSectionName) return;

        const sectionNames = {
            'overview': 'Overview',
            'forecast': 'Forecast',
            'technical': 'Technical Analysis',
            'fundamentals': 'Fundamentals',
            'company': 'Company Details',
            'trading': 'Trading Strategies',
            'conclusion': 'Conclusion'
        };

        const displayName = sectionNames[sectionName] || 'Overview';
        currentSectionName.textContent = displayName;

        // Update icon
        const icons = {
            'overview': 'fa-chart-line',
            'forecast': 'fa-crystal-ball',
            'technical': 'fa-chart-bar',
            'fundamentals': 'fa-calculator',
            'company': 'fa-building',
            'trading': 'fa-bullseye',
            'conclusion': 'fa-flag-checkered'
        };

        const iconElement = mobileDropdownBtn.querySelector('i:first-child');
        if (iconElement) {
            iconElement.className = `fas ${icons[sectionName] || 'fa-chart-line'}`;
        }
    }

    // ===== Keyboard Navigation =====
    function setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Left Arrow - Previous section
            if (e.key === 'ArrowLeft') {
                navigateToPreviousSection();
            }
            // Right Arrow - Next section
            else if (e.key === 'ArrowRight') {
                navigateToNextSection();
            }
            // Number keys 1-7 - Direct section access
            else if (e.key >= '1' && e.key <= '7') {
                const index = parseInt(e.key) - 1;
                if (sections[index]) {
                    switchToSection(sections[index]);
                }
            }
        });
    }

    function navigateToPreviousSection() {
        const currentIndex = sections.indexOf(currentSection);
        if (currentIndex > 0) {
            switchToSection(sections[currentIndex - 1]);
        }
    }

    function navigateToNextSection() {
        const currentIndex = sections.indexOf(currentSection);
        if (currentIndex < sections.length - 1) {
            switchToSection(sections[currentIndex + 1]);
        }
    }

    // ===== URL Hash Management =====
    function setupURLHash() {
        // Check if there's a hash in the URL on load
        const hash = window.location.hash.substring(1);
        if (hash && sections.includes(hash)) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                switchToSection(hash);
            }, 100);
        }

        // Listen for hash changes
        window.addEventListener('hashchange', () => {
            const newHash = window.location.hash.substring(1);
            if (newHash && sections.includes(newHash) && newHash !== currentSection) {
                switchToSection(newHash);
            }
        });
    }

    function updateURLHash(sectionName) {
        // Update URL hash without causing a scroll
        history.replaceState(null, null, `#${sectionName}`);
    }

    // ===== Analytics Tracking =====
    function trackSectionView(sectionName) {
        // Placeholder for analytics tracking
        // You can integrate Google Analytics, Mixpanel, etc. here
        console.log(`Section viewed: ${sectionName}`);
        
        // Example: Google Analytics
        if (window.gtag) {
            gtag('event', 'section_view', {
                'section_name': sectionName,
                'event_category': 'stock_page',
                'event_label': currentSection
            });
        }
    }

    // ===== Smooth Scroll Enhancement =====
    function enhanceSmoothScroll() {
        // Add smooth scroll to all anchor links within sections
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ===== Loading State Management =====
    function showLoading(sectionName) {
        const section = document.getElementById(sectionName);
        if (section) {
            // Add loading class or spinner
            section.classList.add('loading');
        }
    }

    function hideLoading(sectionName) {
        const section = document.getElementById(sectionName);
        if (section) {
            section.classList.remove('loading');
        }
    }

    // ===== Lazy Loading for Heavy Content =====
    function setupLazyLoading() {
        // Observe sections and load content when they become visible
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const section = entry.target;
                        // Load section content if not already loaded
                        loadSectionContent(section.id);
                        observer.unobserve(section);
                    }
                });
            }, {
                rootMargin: '100px'
            });

            // Observe all sections
            sectionContents.forEach(section => {
                observer.observe(section);
            });
        }
    }

    function loadSectionContent(sectionName) {
        // Placeholder for dynamic content loading
        // This would be used if content is loaded via AJAX
        console.log(`Loading content for section: ${sectionName}`);
    }

    // ===== Responsive Utilities =====
    function isMobileView() {
        return window.innerWidth <= 768;
    }

    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            // Close mobile dropdown on resize
            if (!isMobileView()) {
                closeMobileDropdown();
            }
        }, 250);
    });

    // ===== Public API =====
    window.StockPage = {
        switchToSection: switchToSection,
        getCurrentSection: () => currentSection,
        getSections: () => sections,
        navigateNext: navigateToNextSection,
        navigatePrevious: navigateToPreviousSection
    };

    // ===== Initialize on DOM Ready =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ===== Additional Features =====
    
    // Print functionality
    window.addEventListener('beforeprint', () => {
        // Show all sections for printing
        sectionContents.forEach(section => {
            section.classList.add('active');
        });
    });

    window.addEventListener('afterprint', () => {
        // Restore original state after printing
        sectionContents.forEach(section => {
            section.classList.remove('active');
        });
        switchToSection(currentSection);
    });

    // Expose utility for external use
    window.stockPageUtils = {
        showAllSections: function() {
            sectionContents.forEach(section => {
                section.classList.add('active');
            });
        },
        hideAllSections: function() {
            sectionContents.forEach(section => {
                section.classList.remove('active');
            });
        },
        restoreCurrentSection: function() {
            switchToSection(currentSection);
        }
    };

})();
