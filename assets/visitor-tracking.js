// Privacy-friendly visitor tracking
(function() {
    'use strict';
    
    // Get or create session ID
    function getSessionId() {
        let sessionId = sessionStorage.getItem('ti_monitoring_session_id');
        if (!sessionId) {
            sessionId = generateSessionId();
            sessionStorage.setItem('ti_monitoring_session_id', sessionId);
        }
        return sessionId;
    }
    
    // Generate a random session ID
    function generateSessionId() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < 32; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }
    
    // Track page view
    function trackPageView() {
        try {
            const page = window.location.pathname || '/';
            const sessionId = getSessionId();
            const userAgent = navigator.userAgent || '';
            const referrer = document.referrer || '';
            
            // Send tracking data
            fetch('/api/track', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    page: page,
                    session_id: sessionId,
                    user_agent: userAgent,
                    referrer: referrer
                })
            }).catch(function(error) {
                // Silently fail - don't disturb user experience
                console.debug('Tracking failed:', error);
            });
        } catch (error) {
            // Silently fail - don't disturb user experience
            console.debug('Tracking error:', error);
        }
    }
    
    // Track when page is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', trackPageView);
    } else {
        trackPageView();
    }
    
    // Track page visibility changes (when user comes back to tab)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            // Small delay to avoid duplicate tracking
            setTimeout(trackPageView, 1000);
        }
    });
    
})();
