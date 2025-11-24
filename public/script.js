// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const offsetTop = target.offsetTop - 80; // Account for fixed navbar
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    });
});

// Navbar background on scroll
const navbar = document.querySelector('.navbar');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    if (currentScroll > 50) {
        navbar.style.boxShadow = '0 4px 6px -1px rgb(0 0 0 / 0.1)';
    } else {
        navbar.style.boxShadow = 'none';
    }

    lastScroll = currentScroll;
});

// Animate elements on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe feature cards and pricing cards
document.addEventListener('DOMContentLoaded', () => {
    const elements = document.querySelectorAll('.feature-card, .pricing-card, .step');
    elements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Track CTA clicks (for analytics integration)
document.querySelectorAll('.btn-primary, .btn-primary-large, .btn-primary-card').forEach(button => {
    button.addEventListener('click', (e) => {
        // Log CTA click for analytics
        console.log('CTA clicked:', e.target.textContent.trim());

        // Here you would integrate with Google Analytics, Mixpanel, etc.
        // Example: gtag('event', 'cta_click', { 'button_text': e.target.textContent });
    });
});

// Pricing card hover effect enhancement
document.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transition = 'all 0.3s ease';
    });
});

// API Configuration
const API_BASE_URL = 'https://hikeyz-api.onrender.com';

// Handle Stripe Checkout
const handleSignup = async (plan) => {
    console.log('Signup initiated for plan:', plan);

    // Show loading state
    const button = event.target;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Processing...';

    try {
        // Create Stripe Checkout Session
        const response = await fetch(`${API_BASE_URL}/api/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tier: plan, // 'quick' or 'pro'
                success_url: window.location.origin + '/progress.html?session_token={CHECKOUT_SESSION_ID}',
                cancel_url: window.location.origin + '/?canceled=true'
            })
        });

        if (!response.ok) {
            throw new Error('Failed to create checkout session');
        }

        const data = await response.json();

        // Redirect to Stripe Checkout
        if (data.checkout_url) {
            window.location.href = data.checkout_url;
        } else {
            throw new Error('No checkout URL returned');
        }

    } catch (error) {
        console.error('Checkout error:', error);
        alert('Unable to start checkout. Please try again or contact support.');
        button.disabled = false;
        button.textContent = originalText;
    }
};

// Add click handlers to pricing buttons
document.addEventListener('DOMContentLoaded', () => {
    // Quick Download button ($4.99)
    const quickButtons = document.querySelectorAll('[data-plan="quick"]');
    quickButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            handleSignup('quick');
        });
    });

    // Pro Access button ($49.99)
    const proButtons = document.querySelectorAll('[data-plan="pro"]');
    proButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            handleSignup('pro');
        });
    });

    // Handle canceled checkout
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('canceled') === 'true') {
        alert('Checkout was canceled. Feel free to try again when you\'re ready!');
    }
});

// Mobile menu toggle (for future implementation)
const createMobileMenu = () => {
    const nav = document.querySelector('.nav-links');
    const menuButton = document.createElement('button');
    menuButton.className = 'mobile-menu-button';
    menuButton.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <line x1="3" y1="12" x2="21" y2="12" stroke-width="2"/>
            <line x1="3" y1="6" x2="21" y2="6" stroke-width="2"/>
            <line x1="3" y1="18" x2="21" y2="18" stroke-width="2"/>
        </svg>
    `;

    if (window.innerWidth <= 768) {
        const navContent = document.querySelector('.nav-content');
        if (!document.querySelector('.mobile-menu-button')) {
            navContent.appendChild(menuButton);
        }
    }
};

// Initialize on load
window.addEventListener('load', createMobileMenu);
window.addEventListener('resize', createMobileMenu);
