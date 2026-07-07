// for open image
const popup = document.getElementById('imagePopup');
const popupImg = document.querySelector('.popup-img');
const currentIndexEl = document.getElementById('currentIndex');
const totalImagesEl = document.getElementById('totalImages');

const originalImageLinks = Array.from(document.querySelectorAll('.open-image'));

let currentIndex = 0;

function openPopup(index) {
    if (!originalImageLinks[index]) return;

    currentIndex = index;
    const imgSrc = originalImageLinks[index].getAttribute('data-img');
    if (popupImg) popupImg.src = imgSrc;
    if (popup) popup.style.display = 'flex';
    if (currentIndexEl) currentIndexEl.textContent = currentIndex + 1;
    if (totalImagesEl) totalImagesEl.textContent = originalImageLinks.length;
}

function showNext() {
    currentIndex = (currentIndex + 1) % originalImageLinks.length;
    openPopup(currentIndex);
}

function showPrev() {
    currentIndex = (currentIndex - 1 + originalImageLinks.length) % originalImageLinks.length;
    openPopup(currentIndex);
}

// Attach click event to all .open-image elements to open popup at clicked image
document.querySelectorAll('.open-image').forEach(function(link) {
    link.addEventListener('click', function() {
        const imgSrc = this.getAttribute('data-img');
        if (popupImg) popupImg.src = imgSrc;
        if (popup) popup.style.display = 'flex';
    });
});

// Also handle clicks anywhere on document for .open-image (to open popup at correct index)
if (originalImageLinks.length > 0) {
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.open-image');
        if (target) {
            const imgSrc = target.getAttribute('data-img');
            const index = originalImageLinks.findIndex(link => link.getAttribute('data-img') === imgSrc);
            if (index !== -1) {
                openPopup(index);
            }
        }
    });
}

// Safe event binding for close button (only once!)
const closeBtn = document.querySelector('.popup-close');
if (closeBtn) {
    closeBtn.addEventListener('click', () => {
        if (popup) popup.style.display = 'none';
    });
}

const nextBtn = document.querySelector('.popup-next');
if (nextBtn) {
    nextBtn.addEventListener('click', showNext);
}

const prevBtn = document.querySelector('.popup-prev');
if (prevBtn) {
    prevBtn.addEventListener('click', showPrev);
}