// Sidebar functionality
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');

    // Toggle sidebar collapse (Desktop)
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');

            // Rotate icon
            const icon = sidebarToggle.querySelector('svg');
            if (sidebar.classList.contains('collapsed')) {
                icon.innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>'; // Right arrow
            } else {
                icon.innerHTML = '<polyline points="15 18 9 12 15 6"></polyline>'; // Left arrow
            }

            // Save preference
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });

        // Restore preference
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed && window.innerWidth > 1024) {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('expanded');
            const icon = sidebarToggle.querySelector('svg');
            if (icon) {
                icon.innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>';
            }
        }
    }

    // Mobile menu toggle
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024 &&
                sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                e.target !== mobileMenuBtn &&
                !mobileMenuBtn.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }
});
