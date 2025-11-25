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

// API Configuration - Use global if available, otherwise default
const API_BASE_URL = window.API_BASE_URL || 'https://hikeyz-api.onrender.com';

// Package ID mapping (from database schema_credits.sql)
const PACKAGE_IDS = {
    'starter': 1,    // Starter Pack - $25
    'popular': 2,    // Popular Pack - $50
    'premium': 3     // Premium Pack - $100
};

// Handle Stripe Checkout for Credit Packages
const handleCreditPackagePurchase = async (packageName, event) => {
    console.log('handleCreditPackagePurchase called for package:', packageName);
    console.log('Event:', event);

    // Check if user is logged in
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        // User needs to login/register first
        console.log('User not logged in, opening auth modal...');
        // Open auth modal if it exists
        if (typeof window.openAuthModal === 'function') {
            window.openAuthModal();
        } else {
            console.error('openAuthModal function not found');
            alert('Please login or create an account to purchase credit packages.');
            // Try to scroll to signup section as fallback
            const signupSection = document.getElementById('signup') || document.querySelector('#pricing');
            if (signupSection) {
                signupSection.scrollIntoView({ behavior: 'smooth' });
            }
        }
        return;
    }

    // Get package ID
    const packageId = PACKAGE_IDS[packageName];
    if (!packageId) {
        alert('Invalid package selected. Please try again.');
        return;
    }

    // Show loading state
    const button = event.target.closest('a, button') || event.target;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Processing...';

    try {
        // Create Stripe Checkout Session
        const response = await fetch(`${API_BASE_URL}/api/create-checkout-session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_token: sessionToken,
                package_id: packageId,
                success_url: window.location.origin + '/success.html?session_id={CHECKOUT_SESSION_ID}',
                cancel_url: window.location.origin + '/?canceled=true'
            })
        });

        const data = await response.json();

        if (!response.ok) {
            // Handle specific error cases
            if (response.status === 401) {
                alert('Your session has expired. Please login again.');
                localStorage.removeItem('session_token');
                if (typeof window.openAuthModal === 'function') {
                    window.openAuthModal();
                }
            } else if (response.status === 403) {
                alert('Please login with a registered account to purchase credit packages.');
                if (typeof window.openAuthModal === 'function') {
                    window.openAuthModal();
                }
            } else {
                throw new Error(data.error || 'Failed to create checkout session');
            }
            button.disabled = false;
            button.textContent = originalText;
            return;
        }

        // Redirect to Stripe Checkout
        if (data.checkout_url) {
            window.location.href = data.checkout_url;
        } else {
            throw new Error('No checkout URL returned');
        }

    } catch (error) {
        console.error('Checkout error:', error);
        alert('Unable to start checkout: ' + (error.message || 'Please try again or contact support.'));
        button.disabled = false;
        button.textContent = originalText;
    }
};

// Handle legacy time-based plans (Quick Pass, Day Pass, etc.)
const handleTimeBasedPlan = async (plan, event) => {
    console.log('Legacy plan purchase:', plan);
    // For now, show message that these plans are being phased out
    alert('Time-based plans are being phased out. Please create an account to purchase credit packages that never expire!');
    if (typeof window.openAuthModal === 'function') {
        window.openAuthModal();
    } else {
        // Fallback: scroll to pricing section
        const pricingSection = document.getElementById('pricing');
        if (pricingSection) {
            pricingSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
};

// Function to setup pricing button handlers
function setupPricingButtons() {
    console.log('Setting up pricing button handlers...');
    
    // Credit Package buttons (require login)
    const creditPackageButtons = document.querySelectorAll('[data-plan="starter"], [data-plan="popular"], [data-plan="premium"]');
    console.log('Found credit package buttons:', creditPackageButtons.length);
    
    if (creditPackageButtons.length === 0) {
        console.warn('⚠️ No credit package buttons found! Checking all data-plan elements...');
        const allPlanButtons = document.querySelectorAll('[data-plan]');
        console.log('All buttons with data-plan:', allPlanButtons.length);
        allPlanButtons.forEach((btn, idx) => {
            console.log(`Button ${idx + 1}:`, btn.tagName, btn.className, 'Plan:', btn.getAttribute('data-plan'));
        });
    }
    
    creditPackageButtons.forEach((btn, index) => {
        console.log(`Attaching handler to button ${index + 1}:`, btn.getAttribute('data-plan'), btn);
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('✅ Credit package button clicked:', btn.getAttribute('data-plan'));
            const packageName = btn.getAttribute('data-plan');
            handleCreditPackagePurchase(packageName, e);
        }, { capture: true }); // Use capture phase
    });

    // Legacy time-based plan buttons
    const legacyButtons = document.querySelectorAll('[data-plan="quick"], [data-plan="pro"], [data-plan="day"]');
    console.log('Found legacy plan buttons:', legacyButtons.length);
    
    legacyButtons.forEach((btn, index) => {
        console.log(`Attaching handler to legacy button ${index + 1}:`, btn.getAttribute('data-plan'));
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Legacy plan button clicked:', btn.getAttribute('data-plan'));
            const plan = btn.getAttribute('data-plan');
            handleTimeBasedPlan(plan, e);
        });
    });

    // Handle canceled checkout
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('canceled') === 'true') {
        alert('Checkout was canceled. Feel free to try again when you\'re ready!');
    }

    // Handle successful payment return
    const sessionId = urlParams.get('session_id');
    if (sessionId) {
        // User returned from Stripe checkout
        // Verify payment and show success message
        verifyPaymentStatus(sessionId);
    }
    
    // Fallback: Use event delegation for pricing buttons (in case initial setup failed)
    // Only add if not already added
    if (!document.body.hasAttribute('data-pricing-delegation-added')) {
        document.body.setAttribute('data-pricing-delegation-added', 'true');
        document.body.addEventListener('click', (e) => {
            const target = e.target.closest('[data-plan]');
            if (target) {
                const plan = target.getAttribute('data-plan');
                console.log('Event delegation caught click on:', plan, target);
                
                if (['starter', 'popular', 'premium'].includes(plan)) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Handling credit package purchase via delegation');
                    handleCreditPackagePurchase(plan, e);
                } else if (['quick', 'pro', 'day'].includes(plan)) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Handling legacy plan via delegation');
                    handleTimeBasedPlan(plan, e);
                }
            }
        }, true); // Use capture phase to catch earlier
    }
    
    console.log('Pricing button handlers setup complete');
}

// Add click handlers to pricing buttons
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupPricingButtons);
} else {
    // DOM is already ready, run immediately
    setupPricingButtons();
}

// Verify payment status after returning from Stripe
async function verifyPaymentStatus(stripeSessionId) {
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        console.log('No session token found');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/payment/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_token: sessionToken,
                stripe_session_id: stripeSessionId
            })
        });

        const data = await response.json();

        if (response.ok && data.paid) {
            // Payment successful - show success message
            alert(`✅ Payment successful!\n\n${data.message}\n\nYour new balance: ${data.credit_balance} credits (${data.songs_available} songs available)`);
            
            // Redirect to dashboard if it exists
            if (window.location.pathname.includes('success.html')) {
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 2000);
            }
        } else {
            console.log('Payment verification:', data);
        }
    } catch (error) {
        console.error('Error verifying payment:', error);
    }
}

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
