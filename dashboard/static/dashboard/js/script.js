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


/* ===== دیالوگ تأیید برنددار اُرام‌شاپ ===== */
(function () {
    function buildModal() {
        const wrap = document.createElement('div');
        wrap.id = 'osConfirmModal';
        wrap.style.cssText = 'display:none; position:fixed; inset:0; background:rgba(0,0,0,.45);' +
            'backdrop-filter:blur(8px); z-index:99999; align-items:center; justify-content:center;';
        wrap.innerHTML = `
            <div style="background:#fff; border-radius:20px; padding:28px; width:90%; max-width:400px;
                        text-align:center; box-shadow:0 24px 64px rgba(0,0,0,.25); font-family:inherit;">
                <svg width="120" height="26" viewBox="0 0 480 88" style="margin-bottom:14px;">
                    <g fill="none" stroke-linecap="round">
                        <rect x="10" y="14" width="78" height="60" rx="30" stroke="#1A1A1A" stroke-width="13"/>
                        <path d="M30 66 Q52 78 76 60" stroke="#00E6FF" stroke-width="9"/>
                        <path d="M182 20 H136 Q112 20 112 36 Q112 50 136 50 H158 Q182 50 182 62 Q182 76 156 76 H108" stroke="#1A1A1A" stroke-width="13"/>
                    </g>
                    <text x="204" y="60" font-family="Segoe UI, sans-serif" font-size="34" font-weight="700" letter-spacing="6" fill="#1A1A1A">ORAM</text>
                    <text x="204" y="60" dx="122" font-family="Segoe UI, sans-serif" font-size="34" font-weight="300" letter-spacing="6" fill="#00B8CC">SHOP</text>
                </svg>
                <p id="osConfirmMessage" style="font-size:15px; color:#333; margin-bottom:22px; line-height:1.8;"></p>
                <div style="display:flex; gap:10px;">
                    <button id="osConfirmYes"
                            style="flex:1; padding:11px; background:#FF3B30; color:#fff; border:none; border-radius:12px;
                                   font-family:inherit; font-weight:600; cursor:pointer;">بله، انجام بده</button>
                    <button id="osConfirmNo"
                            style="flex:1; padding:11px; background:#f2f2f2; color:#333; border:none; border-radius:12px;
                                   font-family:inherit; font-weight:600; cursor:pointer;">انصراف</button>
                </div>
            </div>`;
        document.body.appendChild(wrap);
        return wrap;
    }

    document.addEventListener('DOMContentLoaded', function () {
        let pendingForm = null;
        const modal = buildModal();
        const msg = document.getElementById('osConfirmMessage');

        document.querySelectorAll('form[data-confirm], form[onsubmit*="confirm"]').forEach(form => {
            const text = form.dataset.confirm ||
                (form.getAttribute('onsubmit') || '').match(/confirm\('([^']+)'\)/)?.[1] ||
                'این عملیات انجام شود؟';
            form.removeAttribute('onsubmit');
            form.dataset.confirm = text;
            form.addEventListener('submit', function (e) {
                if (form.dataset.confirmed === '1') return;
                e.preventDefault();
                pendingForm = form;
                msg.textContent = text;
                modal.style.display = 'flex';
            });
        });

        document.getElementById('osConfirmYes').addEventListener('click', function () {
            if (pendingForm) {
                pendingForm.dataset.confirmed = '1';
                pendingForm.submit();
            }
            modal.style.display = 'none';
        });
        document.getElementById('osConfirmNo').addEventListener('click', function () {
            pendingForm = null;
            modal.style.display = 'none';
        });
        modal.addEventListener('click', function (e) {
            if (e.target === modal) { pendingForm = null; modal.style.display = 'none'; }
        });
    });
})();
