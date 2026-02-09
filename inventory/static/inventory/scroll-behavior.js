document.addEventListener('DOMContentLoaded', function() {
    const floatingCart = document.querySelector('.floating-cart');
    let lastScrollTop = 0;
    let ticking = false;

    window.addEventListener('scroll', function() {
        if (!ticking) {
            window.requestAnimationFrame(function() {
                const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
                
                if (currentScroll > 100) {  // Only hide when scrolled down significantly
                    if (currentScroll > lastScrollTop) {
                        // Scrolling down
                        floatingCart.classList.add('hidden');
                    } else {
                        // Scrolling up
                        floatingCart.classList.remove('hidden');
                    }
                } else {
                    // Near the top, always show
                    floatingCart.classList.remove('hidden');
                }
                
                lastScrollTop = currentScroll;
                ticking = false;
            });

            ticking = true;
        }
    });
});