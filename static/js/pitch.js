document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.slide');
    const progressBar = document.querySelector('.progress-bar');
    let currentSlide = 0;

    function showSlide(index) {
        // Bounds check
        if (index < 0) index = 0;
        if (index >= slides.length) index = slides.length - 1;

        // Update state
        slides.forEach((slide, i) => {
            slide.classList.remove('active', 'prev');
            
            if (i === index) {
                slide.classList.add('active');
            } else if (i < index) {
                slide.classList.add('prev');
            }
        });

        currentSlide = index;
        
        // Update progress bar
        const progress = ((index + 1) / slides.length) * 100;
        if (progressBar) progressBar.style.width = `${progress}%`;

        // Update URL hash without scrolling (optional, for bookmarking)
        // window.location.hash = `slide-${index + 1}`;
    }

    function nextSlide() {
        showSlide(currentSlide + 1);
    }

    function prevSlide() {
        showSlide(currentSlide - 1);
    }

    // Keyboard Navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'Space' || e.key === 'Enter') {
            nextSlide();
        } else if (e.key === 'ArrowLeft') {
            prevSlide();
        } else if (e.key === 'f' || e.key === 'F') {
            toggleFullScreen();
        }
    });

    // Touch Navigation (Simple Swipe)
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, false);

    document.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);

    function handleSwipe() {
        if (touchEndX < touchStartX - 50) {
            nextSlide();
        }
        if (touchEndX > touchStartX + 50) {
            prevSlide();
        }
    }

    function toggleFullScreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        }
    }

    // Expose functions to global scope for buttons
    window.pitchDeck = {
        next: nextSlide,
        prev: prevSlide,
        fullscreen: toggleFullScreen
    };

    // Initialize
    showSlide(0);
});
