// Sidebar Toggle for Mobile
const menuToggle = document.getElementById('menuToggle');
const closeSidebar = document.getElementById('closeSidebar');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');

// Open Sidebar
menuToggle.addEventListener('click', () => {
    sidebar.classList.add('active');
    overlay.classList.add('active');
});

// Close Sidebar
closeSidebar.addEventListener('click', () => {
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
});

// Close Sidebar when clicking overlay
overlay.addEventListener('click', () => {
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
});

// Dropdown Menu Functionality
const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

dropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', (e) => {
        e.preventDefault();
        
        const parentLi = toggle.parentElement;
        const isActive = parentLi.classList.contains('active');
        
        // Close all other dropdowns
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            dropdown.classList.remove('active');
        });
        
        // Toggle current dropdown
        if (!isActive) {
            parentLi.classList.add('active');
        }
    });
});

// Active Menu Item
const menuItems = document.querySelectorAll('.sidebar-nav a:not(.dropdown-toggle)');

menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
        // Remove active class from all items
        document.querySelectorAll('.sidebar-nav > ul > li').forEach(li => {
            li.classList.remove('active');
        });
        
        // Add active class to clicked item's parent li
        const parentLi = item.closest('li');
        if (parentLi && !parentLi.classList.contains('dropdown')) {
            parentLi.classList.add('active');
        }
        
        // Close sidebar on mobile after clicking
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }
    });
});



// Update time dynamically (optional feature)
function updateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    const persianDate = now.toLocaleDateString('fa-IR', options);
    
    // You can add a time element to display this
    // document.getElementById('current-time').textContent = persianDate;
}

// Update every minute
setInterval(updateTime, 60000);
updateTime();

// Handle window resize
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        // Close sidebar on desktop view
        if (window.innerWidth > 768) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }
    }, 250);
});


// Search functionality (basic implementation)
const searchInput = document.querySelector('.search-box input');
if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        // Add your search logic here
        console.log('جستجو برای:', searchTerm);
    });
}

// Table row click handler
const tableRows = document.querySelectorAll('.data-table tbody tr');
tableRows.forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function() {
        // Add your row click logic here
        console.log('ردیف کلیک شد');
    });
});


console.log('🎉 پنل مدیریت با موفقیت بارگذاری شد');

