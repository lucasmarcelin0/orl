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
    
    // Search functionality (exemplo básico)
    const searchBox = document.querySelector('.search-box input');
    const searchButton = document.querySelector('.search-box button');
    
    if (searchBox && searchButton) {
        searchButton.addEventListener('click', function() {
            performSearch(searchBox.value);
        });
        
        searchBox.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch(searchBox.value);
            }
        });
    }
    
    function performSearch(query) {
        if (query.trim() !== '') {
            alert(`Buscando por: ${query}`);
            // Aqui você implementaria a lógica de busca real
        }
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
    const emergencyContacts = document.querySelector('#emergencyContacts');

    if (emergencyToggleButton && emergencyContacts) {
        const hiddenClass = 'is-hidden';
        const showLabel = emergencyToggleButton.dataset.showLabel || 'Mostrar contatos de emergência';
        const hideLabel = emergencyToggleButton.dataset.hideLabel || 'Ocultar contatos de emergência';

        emergencyToggleButton.addEventListener('click', () => {
            const isHidden = emergencyContacts.classList.toggle(hiddenClass);
            emergencyToggleButton.setAttribute('aria-expanded', (!isHidden).toString());
            emergencyToggleButton.textContent = isHidden ? showLabel : hideLabel;
        });
    }
});
