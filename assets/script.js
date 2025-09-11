function toggleAccordion(clickedAccordion) {
    var currentContentHeight = window.getComputedStyle(clickedAccordion.parentElement.getElementsByClassName('accordion-element-content')[0]).height;
    // close clicked accordion element
    if (currentContentHeight != '0px') {
        clickedAccordion.parentElement.getElementsByClassName('accordion-element-content')[0].style.height = '0px';
        clickedAccordion.style.backgroundColor = '';
        clickedAccordion.getElementsByClassName('expand-collapse-icon')[0].textContent = '+';
    }
    // open clicked accordion element and close all other accordion elements
    else {
        var accordionElements = document.getElementsByClassName('accordion-element');
        Array.from(accordionElements).forEach(function(element) {
            title = element.getElementsByClassName('accordion-element-title')[0];
            content = element.getElementsByClassName('accordion-element-content')[0];
            if (title == clickedAccordion) {
                title.style.backgroundColor = 'lightgrey';
                content.style.height =  content.scrollHeight + 'px';
                title.getElementsByClassName('expand-collapse-icon')[0].textContent = '–';
            }
            else {
                title.style.backgroundColor = '';
                content.style.height = '0px';
                title.getElementsByClassName('expand-collapse-icon')[0].textContent = '+';
            }
        });
    }
}

window.addEventListener('click', function(event) {
    const clickedElement = event.target;
    if (clickedElement.classList.contains('accordion-element-title')) {
        toggleAccordion(clickedElement);
    }
});

// Add touch support for hamburger menu on mobile devices
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenus = document.querySelectorAll('details');
    
    hamburgerMenus.forEach(function(details) {
        const summary = details.querySelector('summary');
        
        if (summary) {
            // Add specific identifiers for hamburger menu
            if (summary.querySelector('.material-icons') && summary.querySelector('.material-icons').textContent === 'menu') {
                summary.classList.add('hamburger-menu-trigger');
            }
            
            // Prevent default touch behavior to ensure consistent handling
            summary.addEventListener('touchstart', function(e) {
                // Add visual feedback for touch
                this.style.backgroundColor = '#f0f0f0';
                // Prevent scrolling while touching the menu button
                e.preventDefault();
                e.stopPropagation();
            }, { passive: false });
            
            summary.addEventListener('touchmove', function(e) {
                // Prevent scrolling while touching the menu button
                e.preventDefault();
                e.stopPropagation();
            }, { passive: false });
            
            summary.addEventListener('touchend', function(e) {
                // Remove visual feedback
                this.style.backgroundColor = '';
                
                // Toggle the details element
                if (details.open) {
                    details.open = false;
                } else {
                    // Close other hamburger menus
                    hamburgerMenus.forEach(function(otherDetails) {
                        if (otherDetails !== details && otherDetails.querySelector('.hamburger-menu-trigger')) {
                            otherDetails.open = false;
                        }
                    });
                    details.open = true;
                    
                    // Adjust menu position for small screens
                    adjustMenuPosition(details);
                }
                
                // Prevent default to avoid potential conflicts
                e.preventDefault();
                e.stopPropagation();
            });
            
            // Reset background color on mouse events (for desktop)
            summary.addEventListener('mousedown', function(e) {
                this.style.backgroundColor = '#f0f0f0';
                e.preventDefault();
            });
            
            summary.addEventListener('mouseup', function(e) {
                this.style.backgroundColor = '';
                e.preventDefault();
            });
            
            summary.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
            
            // Handle window resize to adjust menu position
            window.addEventListener('resize', function() {
                if (details.open) {
                    adjustMenuPosition(details);
                }
            });
        }
    });
    
    // Close hamburger menu when clicking outside
    document.addEventListener('click', function(event) {
        hamburgerMenus.forEach(function(details) {
            const summary = details.querySelector('summary');
            const content = details.querySelector('#hamburger-menu-content');
            
            if (summary && content) {
                // Check if click is outside the hamburger menu
                if (!summary.contains(event.target) && !content.contains(event.target)) {
                    details.open = false;
                }
            }
        });
    });
    
    // Also close hamburger menu when touching outside
    document.addEventListener('touchstart', function(event) {
        hamburgerMenus.forEach(function(details) {
            const summary = details.querySelector('summary');
            const content = details.querySelector('#hamburger-menu-content');
            
            if (summary && content) {
                // Check if touch is outside the hamburger menu
                if (!summary.contains(event.target) && !content.contains(event.target)) {
                    details.open = false;
                }
            }
        });
    }, { passive: true });
    
    // Function to adjust menu position based on screen size
    function adjustMenuPosition(details) {
        const content = details.querySelector('#hamburger-menu-content');
        if (!content) return;
        
        // Get viewport dimensions
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Get summary element position
        const summary = details.querySelector('summary');
        const summaryRect = summary.getBoundingClientRect();
        
        // Reset positioning
        content.style.right = '0';
        content.style.left = 'auto';
        
        // Adjust for small screens
        if (viewportWidth <= 480) {
            // On very small screens, ensure menu doesn't go off screen
            const contentWidth = content.offsetWidth || 160;
            if (summaryRect.right + contentWidth > viewportWidth) {
                content.style.right = '0';
                content.style.left = 'auto';
            }
        }
        
        // Ensure menu doesn't go off the top or bottom of the screen
        const contentHeight = content.offsetHeight || 200;
        if (summaryRect.bottom + contentHeight > viewportHeight) {
            // Position above the trigger if there's not enough space below
            content.style.marginTop = '-250px'; // Approximate height of menu + some spacing
        } else {
            content.style.marginTop = '8px';
        }
    }
});

// add favicon to head
var favicon_png = document.createElement('link')
favicon_png.rel = 'apple-touch-icon'
favicon_png.type = 'image/png'
favicon_png.href = 'assets/favicon.png'
document.getElementsByTagName('head')[0].appendChild(favicon_png)
var favicon_svg = document.createElement('icon')
favicon_svg.rel = 'icon'
favicon_svg.type = 'image/svg+xml'
favicon_svg.href = 'assets/logo.svg'
document.getElementsByTagName('head')[0].appendChild(favicon_svg)