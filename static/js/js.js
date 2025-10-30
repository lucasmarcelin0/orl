// Mobile menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const nav = document.querySelector('nav');
    const overlay = document.querySelector('.overlay');
    
    if (mobileMenuBtn && nav && overlay) {
        mobileMenuBtn.addEventListener('click', function() {
            nav.classList.toggle('active');
            overlay.classList.toggle('active');
        });
        
        overlay.addEventListener('click', function() {
            nav.classList.remove('active');
            overlay.classList.remove('active');
        });
    }
    
    // Smooth scrolling para âncoras
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Adicionar classe de scroll ao header
    window.addEventListener('scroll', function() {
        const header = document.querySelector('header');
        if (window.scrollY > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // Normaliza o texto das notícias novas para manter o padrão visual.
    const SUMMARY_LIMIT = 220;
    document.querySelectorAll('.news-card').forEach(card => {
        const summaryElement = card.querySelector('.news-summary');
        if (!summaryElement) {
            return;
        }

        const readMoreLink = card.querySelector('.news-read-more');
        const fullSummary = (summaryElement.dataset.fullSummary || '').trim();

        if (!fullSummary) {
            return;
        }

        if (fullSummary.length <= SUMMARY_LIMIT) {
            summaryElement.textContent = fullSummary;
            return;
        }

        const truncated = fullSummary.slice(0, SUMMARY_LIMIT);
        const lastWhitespace = truncated.lastIndexOf(' ');
        const displayText = lastWhitespace > 0 ? truncated.slice(0, lastWhitespace) : truncated;
        summaryElement.textContent = `${displayText}...`;

        if (readMoreLink) {
            readMoreLink.classList.add('news-read-more--active');
        }
    });

    const emergencyToggleButton = document.querySelector('[data-js="emergency-toggle"]');
    const emergencyPanel = document.querySelector('#emergencyPanel');
    const emergencyContainer = emergencyToggleButton ? emergencyToggleButton.closest('.emergency-container') : null;

    if (emergencyToggleButton && emergencyPanel && emergencyContainer) {
        const showLabel = emergencyToggleButton.dataset.showLabel || 'Mostrar contatos de emergência';
        const hideLabel = emergencyToggleButton.dataset.hideLabel || 'Ocultar contatos de emergência';
        const labelElement = emergencyToggleButton.querySelector('[data-js="emergency-toggle-label"]');
        const iconElement = emergencyToggleButton.querySelector('[data-js="emergency-toggle-icon"]');
        const collapsedClass = 'is-collapsed';

        const updateToggleState = (isCollapsed) => {
            emergencyPanel.hidden = isCollapsed;
            emergencyToggleButton.setAttribute('aria-expanded', (!isCollapsed).toString());
            emergencyToggleButton.setAttribute('title', isCollapsed ? showLabel : hideLabel);

            if (labelElement) {
                labelElement.textContent = isCollapsed ? showLabel : hideLabel;
            }

            if (iconElement) {
                iconElement.classList.toggle('fa-chevron-up', !isCollapsed);
                iconElement.classList.toggle('fa-chevron-down', isCollapsed);
            }
        };

        emergencyToggleButton.addEventListener('click', () => {
            const isCollapsed = emergencyContainer.classList.toggle(collapsedClass);
            updateToggleState(isCollapsed);
        });

        updateToggleState(emergencyContainer.classList.contains(collapsedClass));
    }
});
