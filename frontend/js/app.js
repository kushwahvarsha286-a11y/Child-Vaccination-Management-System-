// ==================================================
// VacciCare – Main Application JavaScript
// ==================================================

// Global state
let currentChildId = null;
let childrenList = [];
let vaccinesList = [];
let currentUser = null;
let carouselInterval = null;
let currentSlideIndex = 0;

// ===== CAROUSEL FUNCTIONS =====
function showSlide(index) {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.dot');
    
    if (slides.length === 0) return;
    
    if (index >= slides.length) {
        currentSlideIndex = 0;
    } else if (index < 0) {
        currentSlideIndex = slides.length - 1;
    } else {
        currentSlideIndex = index;
    }
    
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    
    if (slides[currentSlideIndex]) {
        slides[currentSlideIndex].classList.add('active');
    }
    if (dots[currentSlideIndex]) {
        dots[currentSlideIndex].classList.add('active');
    }
}

function currentSlide(n) {
    clearInterval(carouselInterval);
    showSlide(n);
    startCarousel();
}

function startCarousel() {
    if (carouselInterval) clearInterval(carouselInterval);
    carouselInterval = setInterval(() => {
        showSlide(currentSlideIndex + 1);
    }, 5000);
}

function initCarousel() {
    showSlide(0);
    startCarousel();
}

// ===== HAMBURGER MENU =====
function toggleMenu() {
    const navLinks = document.getElementById('navLinks');
    const hamburger = document.getElementById('hamburgerBtn');
    const overlay = document.getElementById('navOverlay');
    
    navLinks.classList.toggle('active');
    hamburger.classList.toggle('active');
    overlay.classList.toggle('active');
    
    // Prevent body scroll when menu is open
    document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
}

function closeMenu() {
    const navLinks = document.getElementById('navLinks');
    const hamburger = document.getElementById('hamburgerBtn');
    const overlay = document.getElementById('navOverlay');
    
    navLinks.classList.remove('active');
    hamburger.classList.remove('active');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
}

// ===== AUTHENTICATION FUNCTIONS =====
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    
    if (!email || !password) {
        utils.showError('Please fill in all fields');
        return;
    }
    
    try {
        const response = await api.login({ email, password });
        
        if (response.error) {
            // Handle specific error messages
            if (response.error.includes('pending')) {
                utils.showError('Your account is pending admin approval. Please wait for the administrator to review your registration.');
            } else if (response.error.includes('rejected')) {
                utils.showError('Your account registration has been rejected. Please contact the administrator.');
            } else if (response.error.includes('Invalid email or password')) {
                utils.showError('Invalid email or password');
            } else {
                utils.showError(response.error);
            }
            return;
        }
        
        // Extract user data from new response format: { token, user: { id, name, email, role } }
        const token = response.token;
        const user = response.user;
        
        if (!token || !user || !user.role) {
            utils.showError('Invalid server response. Please try again.');
            return;
        }
        
        // Store auth data in localStorage
        localStorage.setItem('userEmail', user.email);
        localStorage.setItem('userName', user.name || 'User');
        localStorage.setItem('userId', user.id);
        localStorage.setItem('isAuthenticated', 'true');
        localStorage.setItem('userToken', token);
        localStorage.setItem('userRole', user.role);
        
        currentUser = {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role
        };
        
        updateNavigationState();
        
        document.getElementById('loginForm').reset();
        
        // Redirect based on role (no alert for successful login)
        setTimeout(() => {
            showPage('dashboard');
        }, 500);
        
    } catch (error) {
        console.error('Login error:', error);
        utils.showError('Failed to connect to server. Please try again.');
    }
}

function normalizeNameInput(value) {
    return value
        .replace(/[^a-zA-Z\s'-]/g, '')
        .split(/\s+/)
        .filter(Boolean)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

function validatePhoneNumber(phone) {
    const digitsOnly = phone.replace(/\D/g, '');
    return /^[6-9]\d{9}$/.test(digitsOnly);
}

function isValidChildDob(dob) {
    const selected = new Date(dob);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return selected instanceof Date && !Number.isNaN(selected.getTime()) && selected < today;
}

function setSignupDobMaxDate() {
    const dobField = document.getElementById('signupChildDob');
    if (!dobField) return;
    const today = new Date();
    today.setDate(today.getDate() - 1);
    dobField.max = today.toISOString().split('T')[0];
}

async function handleSignup(event) {
    event.preventDefault();
    
    const firstNameRaw = document.getElementById('firstName').value.trim();
    const lastNameRaw = document.getElementById('lastName').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value.trim();
    const confirmPassword = document.getElementById('confirmPassword').value.trim();
    const phoneRaw = document.getElementById('phoneNumber').value.trim();
    const address = document.getElementById('signupAddress').value.trim();
    const childNameRaw = document.getElementById('signupChildName').value.trim();
    const childGender = document.getElementById('signupChildGender').value;
    const childDob = document.getElementById('signupChildDob').value;

    const firstName = normalizeNameInput(firstNameRaw);
    const lastName = normalizeNameInput(lastNameRaw);
    const childName = normalizeNameInput(childNameRaw);
    const phone = phoneRaw.replace(/\D/g, '');
    
    document.getElementById('firstName').value = firstName;
    document.getElementById('lastName').value = lastName;
    document.getElementById('signupChildName').value = childName;

    if (!firstName || !lastName || !email || !password || !confirmPassword || !phone || !address) {
        utils.showError('Please fill in all required parent fields');
        return;
    }
    if (!childName || !childGender || !childDob) {
        utils.showError('Please fill in all mandatory child details');
        return;
    }
    if (!validatePhoneNumber(phone)) {
        utils.showError('Phone number must be 10 digits, start with 6-9, and contain no letters');
        return;
    }
    if (!isValidChildDob(childDob)) {
        utils.showError('Date of birth must be earlier than today');
        return;
    }
    if (password !== confirmPassword) {
        utils.showError('Passwords do not match');
        return;
    }
    if (password.length < 6) {
        utils.showError('Password must be at least 6 characters');
        return;
    }
    
    try {
        const response = await api.signupParent({
            first_name: firstName,
            last_name: lastName,
            email: email,
            password: password,
            phone: phone,
            address: address,
            role: 'parent',
            child: {
                name: childName,
                gender: childGender,
                date_of_birth: childDob,
                relation: 'Parent'
            }
        });
        
        if (response.error) {
            utils.showError(response.error);
            return;
        }

        utils.showSuccess(`Welcome to VacciCare, ${firstName}! Your account is ready. Please login.`);
        document.getElementById('signupForm').reset();
        setTimeout(() => showPage('login'), 1500);

    } catch (error) {
        console.error('Signup error:', error);
        utils.showError('Failed to connect to server');
    }
}

async function handleStaffRegister(event) {
    event.preventDefault();
    
    const firstNameRaw = document.getElementById('staffFirstName').value.trim();
    const lastNameRaw = document.getElementById('staffLastName').value.trim();
    const email = document.getElementById('staffEmail').value.trim();
    const password = document.getElementById('staffPassword').value.trim();
    const confirmPassword = document.getElementById('staffConfirmPassword').value.trim();
    const phoneRaw = document.getElementById('staffPhone').value.trim();
    const specialty = document.getElementById('staffSpecialty').value.trim();

    const firstName = normalizeNameInput(firstNameRaw);
    const lastName = normalizeNameInput(lastNameRaw);
    const phone = phoneRaw.replace(/\D/g, '');

    document.getElementById('staffFirstName').value = firstName;
    document.getElementById('staffLastName').value = lastName;
    document.getElementById('staffPhone').value = phone;
    
    if (!firstName || !lastName || !email || !password || !confirmPassword) {
        utils.showError('Please fill in all required fields');
        return;
    }
    if (phone && !validatePhoneNumber(phone)) {
        utils.showError('Phone number must be 10 digits, start with 6-9, and contain no letters');
        return;
    }
    if (password !== confirmPassword) {
        utils.showError('Passwords do not match');
        return;
    }
    if (password.length < 6) {
        utils.showError('Password must be at least 6 characters');
        return;
    }
    
    try {
        const response = await api.registerStaff({
            first_name: firstName,
            last_name: lastName,
            email: email,
            password: password,
            phone: phone,
            specialty: specialty
        });
        
        if (response.error) {
            utils.showError(response.error);
            return;
        }

        utils.showSuccess('Staff registration submitted successfully! Please wait for admin approval.');
        document.getElementById('staffRegisterForm').reset();
        setTimeout(() => showPage('home'), 2000);
    } catch (error) {
        console.error('Staff registration error:', error);
        utils.showError('Registration failed. Please try again.');
    }
}

function logoutUser() {
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userToken');
    localStorage.removeItem('userRole');
    
    currentUser = null;
    updateNavigationState();
    utils.showSuccess('You have been logged out successfully');
    setTimeout(() => showPage('home'), 1500);
}

function handleContact(event) {
    event.preventDefault();
    
    const name = document.getElementById('contactName').value.trim();
    const email = document.getElementById('contactEmail').value.trim();
    const subject = document.getElementById('contactSubject').value.trim();
    const message = document.getElementById('contactMessage').value.trim();
    
    if (!name || !email || !subject || !message) {
        utils.showError('Please fill in all fields');
        return;
    }
    
    utils.showSuccess('Thank you for contacting us! We will get back to you soon.');
    document.getElementById('contactForm').reset();
}

function updateNavigationState() {
    const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
    const role = localStorage.getItem('userRole') || 'parent';
    const userName = localStorage.getItem('userName') || 'User';

    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const staffRegisterBtn = document.getElementById('staffRegisterBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const navUserInfo = document.getElementById('navUserInfo');

    // Toggle public nav links visibility
    document.querySelectorAll('.public-nav-item').forEach(el => {
        el.classList.toggle('hidden', isAuthenticated);
    });

    if (isAuthenticated) {
        // Hide public/auth buttons
        if (loginBtn) loginBtn.classList.add('hidden');
        if (signupBtn) signupBtn.classList.add('hidden');
        if (staffRegisterBtn) staffRegisterBtn.classList.add('hidden'); // KEY FIX
        if (logoutBtn) logoutBtn.classList.remove('hidden');

        // Show user identity with role badge
        if (navUserInfo) {
            const roleLabels = { admin: 'Admin', staff: 'Staff', parent: 'Parent' };
            const roleColors = { admin: '#ef4444', staff: '#8b5cf6', parent: '#10b981' };
            const roleIcons  = { admin: '🛡️', staff: '👨‍⚕️', parent: '👨‍👩‍👧' };
            const label = roleLabels[role] || role;
            const color = roleColors[role] || '#6b7280';
            const icon  = roleIcons[role] || '👤';
            navUserInfo.innerHTML = `
                <div class="nav-user-pill">
                    <span class="nav-user-avatar">${icon}</span>
                    <div class="nav-user-text">
                        <span class="nav-user-name">${escapeHtml(userName)}</span>
                        <span class="nav-role-badge" style="background:${color}">${label}</span>
                    </div>
                </div>
            `;
            navUserInfo.classList.remove('hidden');
        }

        // ── Role-based nav map ──────────────────────────────
        let navMap = {};

        if (role === 'parent') {
            navMap = {
                navDashboard:    true,
                navChildren:     true,   // View my children
                navVaccinations: false,  // Staff/admin only
                navAppointments: true,   // My appointments
                navProviders:    false,  // Not shown to parents
                navStock:        false,
                navAdminUsers:   false,
                navProfile:      true,   // Own profile
                navNotifications: true
            };
        } else if (role === 'staff') {
            navMap = {
                navDashboard:    true,
                navChildren:     true,   // Register/view children
                navVaccinations: false,  // Via children page
                navAppointments: true,   // Schedule appointments
                navProviders:    false,  // Single hospital – no management needed
                navStock:        false,  // Admin only
                navAdminUsers:   false,  // Admin only
                navProfile:      false,
                navNotifications: true
            };
        } else if (role === 'admin') {
            navMap = {
                navDashboard:    true,
                navChildren:     true,   // All children
                navVaccinations: false,  // Via children page
                navAppointments: true,
                navProviders:    false,  // Single hospital – managed via seed
                navStock:        true,   // Manage stock
                navAdminUsers:   true,   // Manage users
                navProfile:      false,
                navNotifications: true
            };
        }

        Object.entries(navMap).forEach(([id, show]) => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle('hidden', !show);
        });

        currentUser = {
            id: localStorage.getItem('userId'),
            email: localStorage.getItem('userEmail'),
            name: userName,
            role: role
        };
    } else {
        // Logged out: restore public state
        if (loginBtn) loginBtn.classList.remove('hidden');
        if (signupBtn) signupBtn.classList.remove('hidden');
        if (staffRegisterBtn) staffRegisterBtn.classList.remove('hidden');
        if (logoutBtn) logoutBtn.classList.add('hidden');
        if (navUserInfo) navUserInfo.classList.add('hidden');

        // Hide all authenticated nav links
        document.querySelectorAll('.auth-nav-item').forEach(item => item.classList.add('hidden'));
        currentUser = null;
    }
}

function initializeAuth() {
    updateNavigationState();
}

// ===== NAVIGATION =====
function showPage(pageId) {
    // Close mobile menu
    closeMenu();
    
    // Stop carousel when leaving home
    if (pageId !== 'home') {
        clearInterval(carouselInterval);
    }
    
    // Check authentication for protected pages
    const protectedPages = ['dashboard', 'children', 'vaccinations', 'appointments', 'notifications', 'stockManagement', 'adminUsers', 'profile'];
    if (protectedPages.includes(pageId) && localStorage.getItem('isAuthenticated') !== 'true') {
        utils.showWarning('Please login to access this page');
        showPage('login');
        return;
    }
    // Role-based access guards
    const role = localStorage.getItem('userRole') || 'parent';
    if (pageId === 'stockManagement' && role !== 'admin') {
        utils.showWarning('Only administrators can manage stock');
        showPage('dashboard');
        return;
    }
    if (pageId === 'adminUsers' && role !== 'admin') {
        utils.showWarning('Only administrators can manage users');
        showPage('dashboard');
        return;
    }
    if (pageId === 'profile' && role !== 'parent') {
        showPage('dashboard');
        return;
    }
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    const page = document.getElementById(pageId);
    if (page) {
        page.classList.add('active');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Start carousel if on home page
        if (pageId === 'home') {
            setTimeout(() => initCarousel(), 100);
        }
        
        // Load page data
        switch(pageId) {
            case 'dashboard': loadDashboard(); break;
            case 'children': loadChildren(); break;
            case 'vaccinations': loadVaccinations(); break;
            case 'appointments': loadAppointments(); break;
            case 'notifications': loadNotifications(); break;
            case 'stockManagement': loadStockManagement(); break;
            case 'adminUsers': loadAdminUsers(); break;
            case 'profile': loadProfile(); break;
        }
    }
}

// ===== DASHBOARD =====
async function loadDashboard() {
    const role = localStorage.getItem('userRole') || 'parent';
    const userName = localStorage.getItem('userName') || 'User';
    
    // Set date
    const dateEl = document.getElementById('dashDate');
    if (dateEl) {
        dateEl.textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }
    
    switch(role) {
        case 'staff': await loadStaffDash(userName); break;
        case 'admin': await loadAdminDash(userName); break;
        default: await loadParentDash(userName); break;
    }
}

// ===== PARENT DASHBOARD =====
async function loadParentDash(userName) {
    try {
        // Fetch data — backend already filters everything to this parent's scope
        const [stats, children, appointments, vaccinations, vaccines] = await Promise.all([
            api.getDashboardStats(),
            api.getChildren(),         // backend: parent_email filtered
            api.getAppointments(),     // backend: parent's children only
            api.getVaccinations(),     // backend: parent's children only
            api.getVaccines()
        ]);
        
        // Welcome
        document.getElementById('dashGreeting').textContent = `Welcome, ${escapeHtml(userName)}! 👋`;
        document.getElementById('dashSubGreeting').textContent = "Here's your family's health overview";
        
        // Stats - PARENT VIEW (all data already scoped to this parent server-side)
        document.getElementById('dashStatsGrid').innerHTML = `
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-icon">👶</div>
                <h3>${children.length}</h3>
                <p>My Children</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stat-icon">💉</div>
                <h3>${vaccinations.filter(v => v.status === 'completed').length}</h3>
                <p>Vaccinations Done</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="stat-icon">📅</div>
                <h3>${appointments.filter(a => a.status === 'scheduled').length}</h3>
                <p>Upcoming Appointments</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="stat-icon">⏳</div>
                <h3>${vaccinations.filter(v => v.status === 'pending').length}</h3>
                <p>Pending Vaccines</p>
            </div>
        `;
        
        // Quick Actions
        document.getElementById('dashQuickActions').innerHTML = `
            <h3>Quick Actions</h3>
            <div class="quick-action-grid">
                <button class="quick-action-btn" onclick="addChild()"><span>👶</span> Add Child</button>
                <button class="quick-action-btn" onclick="openVaccinationModal()"><span>💉</span> Add Vaccination</button>
                <button class="quick-action-btn" onclick="openAppointmentModal()"><span>📅</span> Schedule Appointment</button>
                <button class="quick-action-btn" onclick="showPage('children')"><span>👨‍👩‍👧</span> View Children</button>
            </div>
        `;
        
        // Left: My Children
        let childrenHtml = '<div class="card"><h3>👶 My Children</h3>';
        if (children.length > 0) {
            children.forEach(child => {
                const childVax = vaccinations.filter(v => v.child_id === child.id && v.status === 'completed').length;
                const totalVax = vaccines.length;
                const pct = totalVax > 0 ? Math.round((childVax / totalVax) * 100) : 0;
                childrenHtml += `
                    <div class="child-dash-card">
                        <div class="child-dash-info">
                            <h4>${escapeHtml(child.name)}</h4>
                            <p>Age: ${utils.calculateAge(child.date_of_birth)} | DOB: ${utils.formatDate(child.date_of_birth)}</p>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-label"><span>Vaccination Progress</span><span>${pct}%</span></div>
                            <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
                        </div>
                    </div>
                `;
            });
        } else {
            childrenHtml += '<p class="text-center text-light">No children registered yet. <a href="#" onclick="addChild(); return false;">Add one now</a>.</p>';
        }
        childrenHtml += '</div>';
        
        childrenHtml += '<div class="card mt-20"><h3>📊 Vaccination Progress Overview</h3><div style="position: relative; height:250px; width:100%"><canvas id="parentChart"></canvas></div></div>';
        document.getElementById('dashLeftSection').innerHTML = childrenHtml;
        
        // Draw chart for parent
        setTimeout(() => {
            const ctx = document.getElementById('parentChart');
            if (ctx) {
                const completedCount = vaccinations.filter(v => v.status === 'completed').length;
                const pendingCount = vaccinations.filter(v => v.status === 'pending').length;
                
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Completed', 'Pending'],
                        datasets: [{
                            label: 'Vaccinations',
                            data: [completedCount, pendingCount],
                            backgroundColor: ['#10b981', '#f59e0b'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                    }
                });
            }
        }, 100);
        
        // Right: Upcoming Appointments (already scoped to this parent's children)
        let rightHtml = '<div class="card"><h3>📅 Upcoming Appointments</h3>';
        const scheduled = appointments.filter(a => a.status === 'scheduled').slice(0, 5);
        if (scheduled.length > 0) {
            scheduled.forEach(apt => {
                rightHtml += `
                    <div class="dash-list-item">
                        <div class="dash-list-icon" style="background: #e3f2fd;">📅</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(apt.child_name || 'Unknown')}</h4>
                            <p>${escapeHtml(apt.vaccine_name || 'General')} — ${escapeHtml(apt.provider_name || 'N/A')}</p>
                            <small>${utils.formatDateTime(apt.scheduled_date)}</small>
                        </div>
                        <span class="badge badge-info">Scheduled</span>
                    </div>
                `;
            });
        } else {
            rightHtml += '<p class="text-center text-light">No upcoming appointments.</p>';
        }
        rightHtml += '</div>';
        
        // Recent Vaccinations (already scoped to this parent's children)
        rightHtml += '<div class="card mt-20"><h3>💉 Recent Vaccinations</h3>';
        const recentVax = vaccinations.filter(v => v.status === 'completed').slice(0, 5);
        if (recentVax.length > 0) {
            recentVax.forEach(v => {
                rightHtml += `
                    <div class="dash-list-item">
                        <div class="dash-list-icon" style="background: #e8f5e9;">💉</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(v.vaccine_name || 'Unknown')}</h4>
                            <p>${escapeHtml(v.child_name || 'Child #' + v.child_id)} — ${escapeHtml(v.provider_name || 'N/A')}</p>
                            <small>${utils.formatDate(v.vaccination_date)}</small>
                        </div>
                        <span class="badge badge-success">Done</span>
                    </div>
                `;
            });
        } else {
            rightHtml += '<p class="text-center text-light">No vaccinations recorded yet.</p>';
        }
        rightHtml += '</div>';
        document.getElementById('dashRightSection').innerHTML = rightHtml;
        
        // Full-width: Pending Vaccine Reminders (already scoped to this parent's children)
        let fullHtml = '<div class="card"><h3>⚠️ Pending Vaccine Reminders</h3>';
        const pending = vaccinations.filter(v => v.status === 'pending');
        if (pending.length > 0) {
            pending.forEach(v => {
                const vacDate = new Date(v.vaccination_date);
                const today = new Date();
                const isOverdue = vacDate < today;
                const alertClass = isOverdue ? 'reminder-overdue' : 'reminder-upcoming';
                const label = isOverdue ? 'OVERDUE' : 'UPCOMING';
                fullHtml += `
                    <div class="reminder-card ${alertClass}">
                        <div class="reminder-icon">${isOverdue ? '🔴' : '🟡'}</div>
                        <div class="reminder-info">
                            <h4>${escapeHtml(v.vaccine_name || 'Unknown Vaccine')}</h4>
                            <p>Child: ${escapeHtml(v.child_name || 'Child #' + v.child_id)} | Due: ${utils.formatDate(v.vaccination_date)}</p>
                        </div>
                        <span class="badge ${isOverdue ? 'badge-danger' : 'badge-warning'}">${label}</span>
                    </div>
                `;
            });
        } else {
            fullHtml += '<p class="text-center text-light">🎉 All vaccinations are up to date!</p>';
        }
        fullHtml += '</div>';
        document.getElementById('dashFullSection').innerHTML = fullHtml;
        
    } catch (error) {
        console.error('Error loading parent dashboard:', error);
        document.getElementById('dashStatsGrid').innerHTML = '<p class="text-center text-light">Unable to connect to server.</p>';
    }
}


// ===== STAFF DASHBOARD =====
async function loadStaffDash(userName) {
    try {
        const [stats, children, appointments, vaccinations] = await Promise.all([
            api.getDashboardStats(),
            api.getChildren(),
            api.getAppointments(),
            api.getVaccinations()
        ]);
        
        // Welcome
        const role = localStorage.getItem('userRole') || 'staff';
        const prefix = role === 'admin' ? 'Admin' : 'Dr.';
        document.getElementById('dashGreeting').textContent = `Welcome, ${prefix} ${escapeHtml(userName)}! 🏥`;
        document.getElementById('dashSubGreeting').textContent = "Here's your practice overview";
        
        // Stats
        const todayStr = new Date().toISOString().split('T')[0];
        const todayAppts = appointments.filter(a => a.scheduled_date && a.scheduled_date.startsWith(todayStr));
        const missedVacs = vaccinations.filter(v => v.status === 'pending' && v.vaccination_date < todayStr);
        
        document.getElementById('dashStatsGrid').innerHTML = `
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-icon">👶</div>
                <h3>${stats.children}</h3>
                <p>Total Patients</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stat-icon">📋</div>
                <h3>${todayAppts.length}</h3>
                <p>Today's Schedule</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="stat-icon">💉</div>
                <h3>${stats.vaccinations}</h3>
                <p>Vaccinations Given</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="stat-icon">⚠️</div>
                <h3>${missedVacs.length}</h3>
                <p>Missed Vaccinations</p>
            </div>
        `;
        
        // Quick Actions
        document.getElementById('dashQuickActions').innerHTML = `
            <h3>Quick Actions</h3>
            <div class="quick-action-grid">
                <button class="quick-action-btn" onclick="openAppointmentModal()"><span>📅</span> Schedule Appointment</button>
                <button class="quick-action-btn" onclick="openVaccinationModal()"><span>💉</span> Record Vaccination</button>
                <button class="quick-action-btn" onclick="showPage('children')"><span>👶</span> View All Patients</button>
                <button class="quick-action-btn" onclick="showPage('appointments')"><span>📋</span> All Appointments</button>
            </div>
        `;
        
        // Left: Today's Appointments
        let leftHtml = '<div class="card"><h3>📋 Today\'s Appointments</h3>';
        if (todayAppts.length > 0) {
            todayAppts.forEach(apt => {
                let statusBadge = apt.status === 'completed' ? '<span class="badge badge-success">Done</span>'
                    : apt.status === 'cancelled' ? '<span class="badge badge-danger">Cancelled</span>'
                    : '<span class="badge badge-info">Scheduled</span>';
                leftHtml += `
                    <div class="dash-list-item">
                        <div class="dash-list-icon" style="background: #fff3e0;">📅</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(apt.child_name || 'Unknown')}</h4>
                            <p>${escapeHtml(apt.vaccine_name || 'General Checkup')}</p>
                            <small>${utils.formatDateTime(apt.scheduled_date)}</small>
                        </div>
                        ${statusBadge}
                    </div>
                `;
            });
        } else {
            leftHtml += '<p class="text-center text-light">No appointments today.</p>';
        }
        leftHtml += '</div>';
        
        // Patient Search
        leftHtml += `<div class="card mt-20"><h3>🔍 Patient Search</h3>
            <div class="search-bar">
                <input type="text" id="patientSearchInput" placeholder="Search patients by name..." oninput="searchPatients()">
            </div>
            <div id="patientSearchResults"></div>
        </div>`;
        document.getElementById('dashLeftSection').innerHTML = leftHtml;
        
        // Right: Recent Activity
        let rightHtml = '<div class="card"><h3>📊 Recent Activity</h3>';
        const recentVax = vaccinations.slice(0, 10);
        if (recentVax.length > 0) {
            recentVax.forEach(v => {
                rightHtml += `
                    <div class="dash-list-item">
                        <div class="dash-list-icon" style="background: #e8f5e9;">💉</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(v.vaccine_name || 'Unknown')}</h4>
                            <p>${escapeHtml(v.child_name || 'Child #' + v.child_id)}</p>
                            <small>${utils.formatDate(v.vaccination_date)} — ${v.status}</small>
                        </div>
                        <span class="badge ${v.status === 'completed' ? 'badge-success' : 'badge-warning'}">${v.status}</span>
                    </div>
                `;
            });
        } else {
            rightHtml += '<p class="text-center text-light">No recent activity.</p>';
        }
        rightHtml += '</div>';
        document.getElementById('dashRightSection').innerHTML = rightHtml;
        
        // Full: All upcoming appointments
        let fullHtml = '<div class="card"><h3>📅 All Upcoming Appointments</h3>';
        const upcoming = appointments.filter(a => a.status === 'scheduled').slice(0, 10);
        if (upcoming.length > 0) {
            fullHtml += '<div class="stock-table"><table><thead><tr><th>Child</th><th>Vaccine</th><th>Provider</th><th>Date</th><th>Status</th></tr></thead><tbody>';
            upcoming.forEach(a => {
                fullHtml += `<tr>
                    <td>${escapeHtml(a.child_name || 'Unknown')}</td>
                    <td>${escapeHtml(a.vaccine_name || 'N/A')}</td>
                    <td>${escapeHtml(a.provider_name || 'N/A')}</td>
                    <td>${utils.formatDateTime(a.scheduled_date)}</td>
                    <td><span class="badge badge-info">Scheduled</span></td>
                </tr>`;
            });
            fullHtml += '</tbody></table></div>';
        } else {
            fullHtml += '<p class="text-center text-light">No upcoming appointments.</p>';
        }
        fullHtml += '</div>';
        document.getElementById('dashFullSection').innerHTML = fullHtml;
        
    } catch (error) {
        console.error('Error loading staff dashboard:', error);
        document.getElementById('dashStatsGrid').innerHTML = '<p class="text-center text-light">Unable to connect to server.</p>';
    }
}

// Patient search for staff dashboard
function searchPatients() {
    const query = document.getElementById('patientSearchInput').value.toLowerCase().trim();
    const resultsDiv = document.getElementById('patientSearchResults');
    
    if (!query) { resultsDiv.innerHTML = ''; return; }
    
    const matches = childrenList.filter(c => c.name.toLowerCase().includes(query));
    
    if (matches.length === 0) {
        resultsDiv.innerHTML = '<p class="text-center text-light">No patients found.</p>';
        return;
    }
    
    resultsDiv.innerHTML = matches.map(child => `
        <div class="dash-list-item" style="cursor:pointer" onclick="viewChild(${child.id})">
            <div class="dash-list-icon" style="background:#e3f2fd;">👶</div>
            <div class="dash-list-info">
                <h4>${escapeHtml(child.name)}</h4>
                <p>Age: ${utils.calculateAge(child.date_of_birth)} | Parent: ${escapeHtml(child.parent_name)}</p>
            </div>
            <button class="btn btn-primary btn-small" onclick="event.stopPropagation(); viewChild(${child.id})">View</button>
        </div>
    `).join('');
}

// ===== ADMIN DASHBOARD =====
async function loadAdminDash(userName) {
    try {
        const [stats, stock, children, appointments, vaccinations, notifications] = await Promise.all([
            api.getDashboardStats(),
            api.getVaccineStock(),
            api.getChildren(),
            api.getAppointments(),
            api.getVaccinations(),
            api.getNotifications()
        ]);
        
        // Welcome
        document.getElementById('dashGreeting').textContent = `Admin Dashboard 🛡️`;
        document.getElementById('dashSubGreeting').textContent = `Welcome, ${escapeHtml(userName)} — System Overview`;
        
        // Stats (6 cards)
        const todayStr = new Date().toISOString().split('T')[0];
        const missedVacs = vaccinations.filter(v => v.status === 'pending' && v.vaccination_date < todayStr);
        const lowStockItems = stock.filter(v => v.stock_quantity <= v.stock_threshold);
        document.getElementById('dashStatsGrid').innerHTML = `
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-icon">👶</div>
                <h3>${stats.children}</h3>
                <p>Total Children</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stat-icon">💉</div>
                <h3>${stats.vaccinations}</h3>
                <p>Total Vaccinations</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="stat-icon">⚠️</div>
                <h3>${missedVacs.length}</h3>
                <p>Missed Vaccinations</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="stat-icon">📅</div>
                <h3>${stats.appointments}</h3>
                <p>Total Appointments</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="stat-icon">🔔</div>
                <h3>${stats.unread_notifications}</h3>
                <p>Unread Alerts</p>
            </div>
            <div class="dash-stat-card" style="background: linear-gradient(135deg, ${lowStockItems.length > 0 ? '#ff0844 0%, #ffb199 100%' : '#43e97b 0%, #38f9d7 100%'});">
                <div class="stat-icon">📦</div>
                <h3>${lowStockItems.length}</h3>
                <p>Low Stock Alerts</p>
            </div>
        `;
        
        // Quick Actions
        document.getElementById('dashQuickActions').innerHTML = `
            <h3>Quick Actions</h3>
            <div class="quick-action-grid">
                <button class="quick-action-btn" onclick="showPage('stockManagement')"><span>📦</span> Manage Stock</button>
                <button class="quick-action-btn" onclick="showPage('adminUsers')"><span>👥</span> Manage Users</button>
                <button class="quick-action-btn" onclick="showPage('children')"><span>👶</span> All Children</button>
                <button class="quick-action-btn" onclick="showPage('notifications')"><span>🔔</span> Notifications</button>
            </div>
        `;
        
        // Left: Low Stock Alerts
        let leftHtml = '<div class="card"><h3>🚨 Low Stock Alerts</h3>';
        if (lowStockItems.length > 0) {
            lowStockItems.forEach(v => {
                const isCritical = v.stock_quantity <= Math.floor(v.stock_threshold / 2);
                leftHtml += `
                    <div class="reminder-card ${isCritical ? 'reminder-overdue' : 'reminder-upcoming'}">
                        <div class="reminder-icon">${isCritical ? '🔴' : '🟡'}</div>
                        <div class="reminder-info">
                            <h4>${escapeHtml(v.name)}</h4>
                            <p>Stock: ${v.stock_quantity} | Threshold: ${v.stock_threshold}</p>
                        </div>
                        <span class="badge ${isCritical ? 'badge-danger' : 'badge-warning'}">${isCritical ? 'CRITICAL' : 'LOW'}</span>
                    </div>
                `;
            });
        } else {
            leftHtml += '<p class="text-center text-light">✅ All vaccines are well stocked!</p>';
        }
        leftHtml += '</div>';
        
        // Patient Search
        leftHtml += `<div class="card mt-20"><h3>🔍 Patient Search</h3>
            <div class="search-bar">
                <input type="text" id="patientSearchInput" placeholder="Search patients by name..." oninput="searchPatients()">
            </div>
            <div id="patientSearchResults"></div>
        </div>`;
        
        leftHtml += '<div class="card mt-20"><h3>📈 System Overview</h3><div style="position: relative; height:250px; width:100%"><canvas id="adminChart"></canvas></div></div>';
        document.getElementById('dashLeftSection').innerHTML = leftHtml;
        
        setTimeout(() => {
            const ctx = document.getElementById('adminChart');
            if (ctx) {
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Children', 'Vaccinations', 'Appointments'],
                        datasets: [{
                            data: [stats.children, stats.vaccinations, stats.appointments],
                            backgroundColor: ['#667eea', '#f5576c', '#00f2fe'],
                            borderWidth: 0,
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'right' }
                        }
                    }
                });
            }
        }, 100);
        
        // Right: Recent Notifications
        let rightHtml = '<div class="card"><h3>🔔 Recent Notifications</h3>';
        const recentNotifs = notifications.slice(0, 8);
        if (recentNotifs.length > 0) {
            recentNotifs.forEach(n => {
                rightHtml += `
                    <div class="dash-list-item">
                        <div class="dash-list-icon" style="background: ${n.is_read ? '#f5f5f5' : '#fff3e0'};">${n.is_read ? '📭' : '📬'}</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(n.title)}</h4>
                            <small>${utils.formatDateTime(n.created_at)}</small>
                        </div>
                        <span class="badge ${n.is_read ? 'badge-info' : 'badge-warning'}">${n.is_read ? 'Read' : 'New'}</span>
                    </div>
                `;
            });
        } else {
            rightHtml += '<p class="text-center text-light">No notifications.</p>';
        }
        rightHtml += '</div>';
        document.getElementById('dashRightSection').innerHTML = rightHtml;
        
        // Full: Vaccine Stock Table
        let fullHtml = '<div class="card"><h3>📦 Vaccine Stock Inventory</h3>';
        fullHtml += '<div class="stock-table"><table><thead><tr><th>Vaccine</th><th>Description</th><th>Stock</th><th>Threshold</th><th>Status</th></tr></thead><tbody>';
        stock.forEach(v => {
            const isLow = v.stock_quantity <= v.stock_threshold;
            const isCritical = v.stock_quantity <= Math.floor(v.stock_threshold / 2);
            const statusBadge = isCritical ? '<span class="badge badge-danger">CRITICAL</span>'
                : isLow ? '<span class="badge badge-warning">LOW</span>'
                : '<span class="badge badge-success">OK</span>';
            fullHtml += `<tr class="${isCritical ? 'stock-critical' : isLow ? 'stock-low' : ''}">
                <td><strong>${escapeHtml(v.name)}</strong></td>
                <td>${escapeHtml(v.description || '—')}</td>
                <td>${v.stock_quantity}</td>
                <td>${v.stock_threshold}</td>
                <td>${statusBadge}</td>
            </tr>`;
        });
        fullHtml += '</tbody></table></div></div>';
        document.getElementById('dashFullSection').innerHTML = fullHtml;
        
    } catch (error) {
        console.error('Error loading admin dashboard:', error);
        document.getElementById('dashStatsGrid').innerHTML = '<p class="text-center text-light">Unable to connect to server.</p>';
    }
}


// ===== CHILDREN MANAGEMENT =====
async function loadChildren() {
    try {
        utils.showLoading('childrenContainer');
        const data = await api.getChildren();
        const container = document.getElementById('childrenContainer');
        container.innerHTML = '';

        if (!Array.isArray(data)) {
            console.error('Unexpected children response:', data);
            container.innerHTML = '<p class="text-center text-light">No children found or unable to load children. Please try again.</p>';
            utils.hideLoading('childrenContainer');
            return;
        }

        childrenList = data;
        
        if (childrenList.length === 0) {
            container.innerHTML = '<p class="text-center text-light">No children found. Click "Add New Child" to get started.</p>';
        } else {
            childrenList.forEach(child => {
                const div = document.createElement('div');
                div.className = 'list-item';
                div.innerHTML = `
                    <div class="list-item-content">
                        <h4>${escapeHtml(child.name)}</h4>
                        <p>Age: ${utils.calculateAge(child.date_of_birth)} | DOB: ${utils.formatDate(child.date_of_birth)}</p>
                        <p>Parent: ${escapeHtml(child.parent_name)} | ${escapeHtml(child.parent_email)}</p>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn btn-primary btn-small" onclick="viewChild(${child.id})">View</button>
                        <button class="btn btn-warning btn-small" onclick="editChild(${child.id})">Edit</button>
                        <button class="btn btn-success btn-small" onclick="window.open('${API_BASE_URL}/vaccinations/certificate/${child.id}', '_blank')">Certificate</button>
                        <button class="btn btn-danger btn-small" onclick="deleteChildRecord(${child.id})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        utils.hideLoading('childrenContainer');
    } catch (error) {
        console.error('Error loading children:', error);
        const container = document.getElementById('childrenContainer');
        const message = error?.message === 'Authentication required to load children'
            ? 'Please log in to view your children.'
            : (error?.message || 'Unable to load children. Please ensure the backend is running.');
        container.innerHTML = `<p class="text-center text-light">${message}</p>`;
        utils.hideLoading('childrenContainer');
    }
}

function addChild() {
    utils.resetForm('childForm');
    document.getElementById('childForm').removeAttribute('data-childId');
    utils.openModal('childModal');
}

function editChild(childId) {
    const child = childrenList.find(c => c.id === childId);
    if (child) {
        document.getElementById('childName').value = child.name;
        document.getElementById('childDOB').value = child.date_of_birth;
        document.getElementById('childGender').value = child.gender || '';
        document.getElementById('parentName').value = child.parent_name;
        document.getElementById('parentEmail').value = child.parent_email;
        document.getElementById('parentPhone').value = child.parent_phone || '';
        
        document.getElementById('childForm').dataset.childId = childId;
        utils.openModal('childModal');
    }
}

function viewChild(childId) {
    currentChildId = childId;
    const child = childrenList.find(c => c.id === childId);
    
    if (child) {
        document.getElementById('childDetailsName').textContent = child.name;
        document.getElementById('childDetailsAge').textContent = utils.calculateAge(child.date_of_birth);
        document.getElementById('childDetailsDOB').textContent = utils.formatDate(child.date_of_birth);
        document.getElementById('childDetailsParent').textContent = child.parent_name;
        document.getElementById('childDetailsEmail').textContent = child.parent_email;
        document.getElementById('childDetailsPhone').textContent = child.parent_phone || 'N/A';
        
        document.getElementById('downloadCertBtn').onclick = () => {
            downloadCertificate(child.id);
        };
        
        utils.openModal('childDetailsModal');
    }
}

async function saveChild(event) {
    event.preventDefault();
    
    const form = document.getElementById('childForm');
    const childId = form.dataset.childId;
    
    const data = {
        name: document.getElementById('childName').value,
        date_of_birth: document.getElementById('childDOB').value,
        gender: document.getElementById('childGender').value,
        parent_name: document.getElementById('parentName').value,
        parent_email: document.getElementById('parentEmail').value,
        parent_phone: document.getElementById('parentPhone').value
    };
    
    try {
        if (childId) {
            await api.updateChild(parseInt(childId), data);
            utils.showSuccess('Child record updated successfully');
        } else {
            await api.createChild(data);
            utils.showSuccess('Child record created successfully');
        }
        
        utils.closeModal('childModal');
        form.removeAttribute('data-childId');
        await loadChildren();
    } catch (error) {
        console.error('Error saving child:', error);
        utils.showError('Error saving child record. Please try again.');
    }
}

async function deleteChildRecord(childId) {
    const result = await utils.showConfirm(
        'Delete Child Record?',
        'Are you sure you want to delete this child record? This action cannot be undone.',
        'Yes, Delete',
        'Cancel',
        true
    );
    
    if (result.isConfirmed) {
        try {
            await api.deleteChild(childId);
            utils.showSuccess('Child record deleted successfully');
            await loadChildren();
        } catch (error) {
            console.error('Error deleting child:', error);
            utils.showError('Error deleting child record');
        }
    }
}

// ===== VACCINATIONS MANAGEMENT =====
async function loadVaccinations() {
    try {
        utils.showLoading('vaccinationsContainer');
        vaccinesList = await api.getVaccines();
        const vaccinations = await api.getVaccinations();
        const container = document.getElementById('vaccinationsContainer');
        container.innerHTML = '';
        
        if (vaccinations.length === 0) {
            container.innerHTML = '<p class="text-center text-light">No vaccinations recorded yet. Click "Add Vaccination Record" to get started.</p>';
        } else {
            vaccinations.forEach(vac => {
                const div = document.createElement('div');
                div.className = 'list-item';
                const statusBadge = vac.status === 'completed' ? 
                    '<span class="badge badge-success">Completed</span>' :
                    '<span class="badge badge-warning">Pending</span>';
                
                div.innerHTML = `
                    <div class="list-item-content">
                        <h4>${escapeHtml(vac.vaccine_name || 'Unknown Vaccine')}</h4>
                        <p>Child ID: ${vac.child_id} | Date: ${utils.formatDate(vac.vaccination_date)}</p>
                        <p>Status: ${statusBadge}</p>
                        ${vac.notes ? `<p>Notes: ${escapeHtml(vac.notes)}</p>` : ''}
                    </div>
                    <div class="list-item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteVaccination(${vac.id})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        utils.hideLoading('vaccinationsContainer');
    } catch (error) {
        console.error('Error loading vaccinations:', error);
        const container = document.getElementById('vaccinationsContainer');
        container.innerHTML = '<p class="text-center text-light">Unable to load vaccinations. Please ensure the backend is running.</p>';
        utils.hideLoading('vaccinationsContainer');
    }
}

// ===== STOCK MANAGEMENT (Admin) =====
async function loadStockManagement() {
    try {
        const stock = await api.getVaccineStock();
        const container = document.getElementById('stockTableContainer');
        
        let html = '<div class="stock-table"><table><thead><tr><th>Vaccine</th><th>Description</th><th>Current Stock</th><th>Alert Threshold</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
        stock.forEach(v => {
            const isLow = v.stock_quantity <= v.stock_threshold;
            const isCritical = v.stock_quantity <= Math.floor(v.stock_threshold / 2);
            const statusBadge = isCritical ? '<span class="badge badge-danger">CRITICAL</span>'
                : isLow ? '<span class="badge badge-warning">LOW</span>'
                : '<span class="badge badge-success">OK</span>';
            html += `<tr class="${isCritical ? 'stock-critical' : isLow ? 'stock-low' : ''}">
                <td><strong>${escapeHtml(v.name)}</strong></td>
                <td>${escapeHtml(v.description || '—')}</td>
                <td><input type="number" class="stock-input" id="stock_${v.id}" value="${v.stock_quantity}" min="0"></td>
                <td><input type="number" class="stock-input" id="threshold_${v.id}" value="${v.stock_threshold}" min="0"></td>
                <td>${statusBadge}</td>
                <td><button class="btn btn-primary btn-small" onclick="updateStock(${v.id})">Update</button></td>
            </tr>`;
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading stock:', error);
        document.getElementById('stockTableContainer').innerHTML = '<p class="text-center text-light">Unable to load stock data.</p>';
    }
}

async function updateStock(vaccineId) {
    const qty = parseInt(document.getElementById(`stock_${vaccineId}`).value);
    const threshold = parseInt(document.getElementById(`threshold_${vaccineId}`).value);
    
    try {
        await api.updateVaccineStock(vaccineId, { stock_quantity: qty, stock_threshold: threshold });
        utils.showSuccess('Stock updated successfully');
        await loadStockManagement();
    } catch (error) {
        console.error('Error updating stock:', error);
        utils.showError('Error updating stock');
    }
}

async function openVaccinationModal() {
    utils.resetForm('vaccinationForm');
    
    try {
        [childrenList, vaccinesList] = await Promise.all([
            api.getChildren(),
            api.getVaccines()
        ]);
        
        populateSelect('vaccinationChild', childrenList, 'name', 'Select Child');
        populateSelect('vaccinationVaccine', vaccinesList, 'name', 'Select Vaccine');
    } catch (error) {
        console.error('Error loading data:', error);
        utils.showError('Error loading form data. Please ensure the backend is running.');
        return;
    }
    
    utils.openModal('vaccinationModal');
}

async function saveVaccination(event) {
    event.preventDefault();
    
    const data = {
        child_id: parseInt(document.getElementById('vaccinationChild').value),
        vaccine_id: parseInt(document.getElementById('vaccinationVaccine').value),
        vaccination_date: document.getElementById('vaccinationDate').value,
        status: document.getElementById('vaccinationStatus').value,
        notes: document.getElementById('vaccinationNotes').value
    };
    
    try {
        await api.createVaccination(data);
        utils.showSuccess('Vaccination record created successfully');
        utils.closeModal('vaccinationModal');
        await loadVaccinations();
    } catch (error) {
        console.error('Error saving vaccination:', error);
        utils.showError('Error saving vaccination. Please try again.');
    }
}

async function deleteVaccination(vaccinationId) {
    const result = await utils.showConfirm(
        'Delete Vaccination Record?',
        'Are you sure you want to delete this vaccination record?',
        'Yes, Delete',
        'Cancel',
        true
    );
    
    if (result.isConfirmed) {
        try {
            await api.deleteVaccination(vaccinationId);
            utils.showSuccess('Vaccination record deleted successfully');
            await loadVaccinations();
        } catch (error) {
            console.error('Error deleting vaccination:', error);
            utils.showError('Error deleting vaccination');
        }
    }
}

// ===== APPOINTMENTS MANAGEMENT =====
async function loadAppointments() {
    try {
        utils.showLoading('appointmentsContainer');
        const role = localStorage.getItem('userRole') || 'parent';
        const appointments = await api.getAppointments();
        const container = document.getElementById('appointmentsContainer');
        container.innerHTML = '';
        
        if (appointments.length === 0) {
            const msg = role === 'parent'
                ? "You have no appointments scheduled for your children yet. Click \"Schedule Appointment\" to book one."
                : 'No appointments scheduled yet. Click \"Schedule Appointment\" to get started.';
            container.innerHTML = `<p class="text-center text-light">${msg}</p>`;
        } else {
            appointments.forEach(apt => {
                const div = document.createElement('div');
                div.className = 'list-item';
                
                let statusBadge;
                switch(apt.status) {
                    case 'scheduled':
                        statusBadge = '<span class="badge badge-info">Scheduled</span>';
                        break;
                    case 'completed':
                        statusBadge = '<span class="badge badge-success">Completed</span>';
                        break;
                    default:
                        statusBadge = '<span class="badge badge-danger">Cancelled</span>';
                }
                
                div.innerHTML = `
                    <div class="list-item-content">
                        <h4>${escapeHtml(apt.child_name || 'Unknown')}</h4>
                        <p>Provider: ${escapeHtml(apt.provider_name || 'N/A')}</p>
                        <p>Date: ${utils.formatDateTime(apt.scheduled_date)}</p>
                        <p>Vaccine: ${escapeHtml(apt.vaccine_name || 'N/A')} | Status: ${statusBadge}</p>
                    </div>
                    <div class="list-item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteAppointment(${apt.id})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        utils.hideLoading('appointmentsContainer');
    } catch (error) {
        console.error('Error loading appointments:', error);
        const container = document.getElementById('appointmentsContainer');
        container.innerHTML = '<p class="text-center text-light">Unable to load appointments. Please ensure the backend is running.</p>';
        utils.hideLoading('appointmentsContainer');
    }
}

async function openAppointmentModal() {
    utils.resetForm('appointmentForm');
    
    try {
        [childrenList, vaccinesList] = await Promise.all([
            api.getChildren(),
            api.getVaccines()
        ]);
        
        populateSelect('appointmentChild', childrenList, 'name', 'Select Child');
        populateSelect('appointmentVaccine', vaccinesList, 'name', 'Select Vaccine');
    } catch (error) {
        console.error('Error loading data:', error);
        utils.showError('Error loading form data. Please ensure the backend is running.');
        return;
    }
    
    utils.openModal('appointmentModal');
}

async function saveAppointment(event) {
    event.preventDefault();
    
    const data = {
        child_id: parseInt(document.getElementById('appointmentChild').value),
        scheduled_date: document.getElementById('appointmentDateTime').value,
        vaccine_id: parseInt(document.getElementById('appointmentVaccine').value) || null,
        status: document.getElementById('appointmentStatus').value,
        notes: document.getElementById('appointmentNotes').value
    };
    
    try {
        await api.createAppointment(data);
        utils.showSuccess('Appointment scheduled successfully');
        utils.closeModal('appointmentModal');
        await loadAppointments();
    } catch (error) {
        console.error('Error saving appointment:', error);
        utils.showError('Error scheduling appointment. Please try again.');
    }
}

async function deleteAppointment(appointmentId) {
    const result = await utils.showConfirm(
        'Delete Appointment?',
        'Are you sure you want to delete this appointment?',
        'Yes, Delete',
        'Cancel',
        true
    );
    
    if (result.isConfirmed) {
        try {
            await api.deleteAppointment(appointmentId);
            utils.showSuccess('Appointment deleted successfully');
            await loadAppointments();
        } catch (error) {
            console.error('Error deleting appointment:', error);
            utils.showError('Error deleting appointment');
        }
    }
}

// ===== HOSPITAL INFO (City Hospital – Single Provider) =====
async function loadProviders() {
    const container = document.getElementById('providersContainer');
    if (!container) return;
    container.innerHTML = `
        <div class="card" style="border-left: 4px solid #667eea; padding: 24px; margin-bottom: 16px;">
            <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;">
                <div style="font-size:3rem;">🏥</div>
                <div>
                    <h3 style="margin:0; color:#1e293b;">City Hospital</h3>
                    <span style="background:#10b981; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.8rem;">Official Partner Hospital</span>
                </div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
                <div class="info-item">
                    <strong>🏢 Type:</strong> Hospital
                </div>
                <div class="info-item">
                    <strong>📍 Address:</strong> 123 Healthcare Avenue, Medical District
                </div>
                <div class="info-item">
                    <strong>📞 Phone:</strong> +91-9876543210
                </div>
                <div class="info-item">
                    <strong>✉️ Email:</strong> info@cityhospital.com
                </div>
                <div class="info-item">
                    <strong>🌐 Website:</strong> www.cityhospital.com
                </div>
            </div>
            <div style="margin-top:16px; padding:12px; background:#f0fdf4; border-radius:8px; border:1px solid #bbf7d0;">
                <p style="margin:0; color:#166534;">✅ All vaccination records and appointments are automatically associated with City Hospital.</p>
            </div>
        </div>
    `;
}

// ===== NOTIFICATIONS =====
async function loadNotifications() {
    try {
        utils.showLoading('notificationsContainer');
        const notifications = await api.getNotifications();
        const container = document.getElementById('notificationsContainer');
        container.innerHTML = '';
        
        if (notifications.length === 0) {
            container.innerHTML = '<p class="text-center text-light">No notifications.</p>';
        } else {
            notifications.forEach(notif => {
                const div = document.createElement('div');
                div.className = `notification-item ${notif.is_read ? '' : 'unread'}`;
                div.innerHTML = `
                    <div class="notification-content">
                        <h4>${escapeHtml(notif.title)}</h4>
                        <p>${escapeHtml(notif.message)}</p>
                        <small class="notification-time">${utils.formatDateTime(notif.created_at)}</small>
                    </div>
                    <div class="list-item-actions">
                        ${!notif.is_read ? `<button class="btn btn-primary btn-small" onclick="markAsRead(${notif.id})">Mark Read</button>` : ''}
                        <button class="btn btn-danger btn-small" onclick="deleteNotif(${notif.id})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }
        
        utils.hideLoading('notificationsContainer');
    } catch (error) {
        console.error('Error loading notifications:', error);
        const container = document.getElementById('notificationsContainer');
        container.innerHTML = '<p class="text-center text-light">Unable to load notifications.</p>';
        utils.hideLoading('notificationsContainer');
    }
}

async function markAsRead(notificationId) {
    try {
        await api.markNotificationAsRead(notificationId);
        utils.showSuccess('Notification marked as read');
        await loadNotifications();
    } catch (error) {
        console.error('Error marking notification as read:', error);
        utils.showError('Error updating notification');
    }
}

async function deleteNotif(notificationId) {
    const result = await utils.showConfirm(
        'Delete Notification?',
        'Are you sure you want to delete this notification? This cannot be undone.',
        'Yes, Delete',
        'Cancel',
        true
    );
    if (!result.isConfirmed) return;
    try {
        await api.deleteNotification(notificationId);
        utils.showToast('Notification deleted', 'success');
        await loadNotifications();
    } catch (error) {
        console.error('Error deleting notification:', error);
        utils.showError('Error deleting notification');
    }
}

// ===== MODAL MANAGEMENT =====
function closeChildModal() {
    utils.closeModal('childModal');
    document.getElementById('childForm').removeAttribute('data-childId');
}

function closeChildDetailsModal() {
    utils.closeModal('childDetailsModal');
    currentChildId = null;
}

function closeVaccinationModal() {
    utils.closeModal('vaccinationModal');
}

function closeAppointmentModal() {
    utils.closeModal('appointmentModal');
}

function closeProviderModal() {
    utils.closeModal('providerModal');
    document.getElementById('providerForm').removeAttribute('data-providerId');
}

// Close modals on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal') && e.target.classList.contains('active')) {
        const modalId = e.target.id;
        switch(modalId) {
            case 'childModal': closeChildModal(); break;
            case 'childDetailsModal': closeChildDetailsModal(); break;
            case 'vaccinationModal': closeVaccinationModal(); break;
            case 'appointmentModal': closeAppointmentModal(); break;
            case 'providerModal': closeProviderModal(); break;
        }
    }
});

// Close modals on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            const modalId = modal.id;
            switch(modalId) {
                case 'childModal': closeChildModal(); break;
                case 'childDetailsModal': closeChildDetailsModal(); break;
                case 'vaccinationModal': closeVaccinationModal(); break;
                case 'appointmentModal': closeAppointmentModal(); break;
                case 'providerModal': closeProviderModal(); break;
            }
        });
    }
});

// ===== HELPER FUNCTIONS =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function populateSelect(selectId, items, labelKey, placeholder) {
    const select = document.getElementById(selectId);
    select.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach(item => {
        select.innerHTML += `<option value="${item.id}">${escapeHtml(item[labelKey])}</option>`;
    });
}


// ===== ADMIN – USER MANAGEMENT =====
async function loadAdminUsers() {
    try {
        const [staffRes, usersRes, pendingRes] = await Promise.all([
            api.adminGetStaff(),
            api.adminGetUsers(),
            api.adminGetPendingStaff()
        ]);

        // Pending Staff table
        const pendingContainer = document.getElementById('adminPendingStaffContainer');
        const pendingList = pendingRes.pending_staff || [];
        if (pendingList.length === 0) {
            pendingContainer.innerHTML = '<p class="text-center text-light">No pending staff registrations.</p>';
        } else {
            let html = '<div class="stock-table"><table><thead><tr><th>Name</th><th>Email</th><th>Workplace</th><th>Specialty</th><th>Applied</th><th>Actions</th></tr></thead><tbody>';
            pendingList.forEach(s => {
                html += `<tr>
                    <td><strong>${escapeHtml(s.first_name)} ${escapeHtml(s.last_name)}</strong></td>
                    <td>${escapeHtml(s.email)}</td>
                    <td>${escapeHtml(s.workplace || '—')}</td>
                    <td>${escapeHtml(s.specialty || '—')}</td>
                    <td>${utils.formatDate(s.created_at)}</td>
                    <td>
                        <button class="btn btn-success btn-small" onclick="approvePendingStaff(${s.id})">Approve</button>
                        <button class="btn btn-danger btn-small" onclick="rejectPendingStaff(${s.id})">Reject</button>
                    </td>
                </tr>`;
            });
            html += '</tbody></table></div>';
            pendingContainer.innerHTML = html;
        }

        // Staff table
        const staffContainer = document.getElementById('adminStaffContainer');
        const staffList = staffRes.staff || [];
        if (staffList.length === 0) {
            staffContainer.innerHTML = '<p class="text-center text-light">No staff accounts found.</p>';
        } else {
            let html = '<div class="stock-table"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Specialty</th><th>Workplace</th><th>Actions</th></tr></thead><tbody>';
            staffList.forEach(s => {
                html += `<tr>
                    <td><strong>${escapeHtml(s.first_name)} ${escapeHtml(s.last_name)}</strong></td>
                    <td>${escapeHtml(s.email)}</td>
                    <td><span class="badge ${s.role === 'admin' ? 'badge-danger' : 'badge-info'}">${s.role}</span></td>
                    <td>${escapeHtml(s.specialty || '—')}</td>
                    <td>${escapeHtml(s.workplace || '—')}</td>
                    <td>${s.role !== 'admin' ? `<button class="btn btn-danger btn-small" onclick="deleteAdminStaff(${s.id})">Delete</button>` : '<span class="text-light">Protected</span>'}</td>
                </tr>`;
            });
            html += '</tbody></table></div>';
            staffContainer.innerHTML = html;
        }

        // Parents table
        const parentsContainer = document.getElementById('adminParentsContainer');
        const users = usersRes.users || [];
        const parents = users.filter(u => u.role === 'parent');
        if (parents.length === 0) {
            parentsContainer.innerHTML = '<p class="text-center text-light">No parent accounts found.</p>';
        } else {
            let html = '<div class="stock-table"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Address</th><th>Joined</th><th>Actions</th></tr></thead><tbody>';
            parents.forEach(p => {
                html += `<tr>
                    <td><strong>${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}</strong></td>
                    <td>${escapeHtml(p.email)}</td>
                    <td>${escapeHtml(p.phone || '—')}</td>
                    <td>${escapeHtml(p.address || '—')}</td>
                    <td>${utils.formatDate(p.created_at)}</td>
                    <td><button class="btn btn-danger btn-small" onclick="deleteAdminUser(${p.id})">Delete</button></td>
                </tr>`;
            });
            html += '</tbody></table></div>';
            parentsContainer.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading admin users:', error);
        utils.showError('Failed to load user data');
    }
}

function openAddStaffModal() {
    document.getElementById('addStaffForm').reset();
    utils.openModal('addStaffModal');
}

function closeAddStaffModal() {
    utils.closeModal('addStaffModal');
}

async function handleAddStaff(event) {
    event.preventDefault();
    const firstName = document.getElementById('newStaffFirstName').value.trim();
    const lastName = document.getElementById('newStaffLastName').value.trim();
    const email = document.getElementById('newStaffEmail').value.trim();
    const phone = document.getElementById('newStaffPhone').value.trim();
    const specialty = document.getElementById('newStaffSpecialty').value.trim();
    const workplace = document.getElementById('newStaffWorkplace').value.trim();
    const password = document.getElementById('newStaffPassword').value.trim();

    if (!firstName || !lastName || !email || !password) {
        utils.showError('First name, last name, email and password are required');
        return;
    }
    if (password.length < 6) {
        utils.showError('Password must be at least 6 characters');
        return;
    }

    try {
        const response = await api.adminCreateStaff({
            first_name: firstName,
            last_name: lastName,
            email,
            phone,
            specialty,
            workplace,
            password
        });

        if (response.error) {
            utils.showError(response.error);
            return;
        }

        utils.showSuccess(`Staff account for ${firstName} created successfully!`);
        closeAddStaffModal();
        await loadAdminUsers();
    } catch (error) {
        console.error('Error creating staff:', error);
        utils.showError('Failed to create staff account');
    }
}

async function deleteAdminStaff(staffId) {
    const result = await utils.showConfirm(
        'Delete Staff Account?',
        'Are you sure you want to delete this staff account? This cannot be undone.',
        'Yes, Delete',
        'Cancel',
        true
    );
    
    if (!result.isConfirmed) return;
    
    try {
        const response = await api.adminDeleteStaff(staffId);
        if (response.error) {
            utils.showError(response.error);
            return;
        }
        utils.showSuccess('Staff account deleted successfully');
        await loadAdminUsers();
    } catch (error) {
        console.error('Error deleting staff:', error);
        utils.showError('Failed to delete staff account');
    }
}

async function deleteAdminUser(userId) {
    const result = await utils.showConfirm(
        'Delete Parent Account?',
        'Are you sure you want to delete this parent account? This cannot be undone.',
        'Yes, Delete',
        'Cancel',
        true
    );
    
    if (!result.isConfirmed) return;
    
    try {
        const response = await api.adminDeleteUser(userId);
        if (response.error) {
            utils.showError(response.error);
            return;
        }
        utils.showSuccess('User deleted successfully');
        await loadAdminUsers();
    } catch (error) {
        console.error('Error deleting user:', error);
        utils.showError('Failed to delete user account');
    }
}

async function approvePendingStaff(staffId) {
    const result = await utils.showConfirm(
        'Approve Staff Registration?',
        'Are you sure you want to approve this staff registration? They will receive login credentials via email.',
        'Yes, Approve',
        'Cancel'
    );
    
    if (!result.isConfirmed) return;
    
    try {
        const response = await api.adminApproveStaff(staffId);
        if (response.error) {
            utils.showError(response.error);
            return;
        }
        utils.showSuccess('Staff registration approved successfully. Credentials sent via email.');
        await loadAdminUsers();
    } catch (error) {
        console.error('Error approving staff:', error);
        utils.showError('Failed to approve staff registration');
    }
}

async function rejectPendingStaff(staffId) {
    const result = await utils.showConfirm(
        'Reject Staff Registration?',
        'Are you sure you want to reject this staff registration? This cannot be undone.',
        'Yes, Reject',
        'Cancel',
        true
    );
    
    if (!result.isConfirmed) return;
    
    try {
        const response = await api.adminRejectStaff(staffId);
        if (response.error) {
            utils.showError(response.error);
            return;
        }
        utils.showSuccess('Staff registration rejected successfully');
        await loadAdminUsers();
    } catch (error) {
        console.error('Error rejecting staff:', error);
        utils.showError('Failed to reject staff registration');
    }
}

// ===== PARENT PROFILE =====
async function loadProfile() {
    const container = document.getElementById('profileContent');
    container.innerHTML = '<p class="text-center text-light">Loading profile...</p>';
    try {
        const res = await api.getProfile();
        if (res.error) {
            container.innerHTML = `<p class="text-center text-light">${res.error}</p>`;
            return;
        }
        const u = res.user;
        const children = res.children || [];

        container.innerHTML = `
            <form id="profileForm" onsubmit="submitProfileUpdate(event)">
                <div class="profile-section">
                    <h3><i class="fas fa-user"></i> Personal Information</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>First Name</label>
                            <input type="text" id="profileFirstName" value="${escapeHtml(u.first_name)}" required>
                        </div>
                        <div class="form-group">
                            <label>Last Name</label>
                            <input type="text" id="profileLastName" value="${escapeHtml(u.last_name)}" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Email Address</label>
                        <input type="email" value="${escapeHtml(u.email)}" disabled class="input-disabled">
                        <small class="form-hint">Email cannot be changed.</small>
                    </div>
                    <div class="form-group">
                        <label>Contact Number</label>
                        <input type="tel" id="profilePhone" value="${escapeHtml(u.phone || '')}">
                    </div>
                    <div class="form-group">
                        <label>Address</label>
                        <input type="text" id="profileAddress" value="${escapeHtml(u.address || '')}">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Save Changes</button>
            </form>
            ${children.length > 0 ? `
            <div class="profile-section mt-20">
                <h3><i class="fas fa-child"></i> My Children (${children.length})</h3>
                ${children.map(c => `
                    <div class="dash-list-item">
                        <div class="dash-list-icon">👶</div>
                        <div class="dash-list-info">
                            <h4>${escapeHtml(c.name)}</h4>
                            <p>${utils.formatDate(c.date_of_birth)} · ${c.gender || 'N/A'}</p>
                        </div>
                        <button class="btn btn-success btn-small" onclick="downloadCertificate(${c.id})">
                            <i class="fas fa-file-pdf"></i> Certificate
                        </button>
                    </div>
                `).join('')}
            </div>` : ''}
        `;
    } catch (error) {
        console.error('Error loading profile:', error);
        container.innerHTML = '<p class="text-center text-light">Failed to load profile.</p>';
    }
}

async function submitProfileUpdate(event) {
    event.preventDefault();
    try {
        const res = await api.updateProfile({
            first_name: document.getElementById('profileFirstName').value.trim(),
            last_name: document.getElementById('profileLastName').value.trim(),
            phone: document.getElementById('profilePhone').value.trim(),
            address: document.getElementById('profileAddress').value.trim()
        });
        if (res.error) {
            utils.showError(res.error);
            return;
        }
        localStorage.setItem('userName', res.user.first_name + ' ' + res.user.last_name);
        utils.showSuccess('Profile updated successfully!');
    } catch (error) {
        utils.showError('Failed to save profile changes');
    }
}

// ===== PDF CERTIFICATE DOWNLOAD =====
async function downloadCertificate(childId) {
    try {
        utils.showInfo('Generating PDF certificate...');
        const genRes = await api.generateReport(childId);
        if (genRes.error) {
            utils.showError(genRes.error || 'Failed to generate certificate');
            return;
        }
        // Backend returns { report_id, report: { id, ... } }
        const reportId = genRes.report_id || (genRes.report && genRes.report.id) || genRes.id;
        if (!reportId) {
            utils.showError('Generated but could not get report ID');
            return;
        }
        const blob = await api.downloadReport(reportId);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vaccination_certificate_child_${childId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        utils.showSuccess('Certificate downloaded!');
    } catch (error) {
        console.error('Certificate download error:', error);
        // Ultimate fallback
        window.open(`http://localhost:5000/api/vaccinations/certificate/${childId}`, '_blank');
    }
}

// ===== INITIALIZE APP =====
window.addEventListener('DOMContentLoaded', () => {
    initializeAuth();
    showPage('home');
    setSignupDobMaxDate();

    const firstNameField = document.getElementById('firstName');
    const lastNameField = document.getElementById('lastName');
    const childNameField = document.getElementById('signupChildName');
    const phoneField = document.getElementById('phoneNumber');

    if (firstNameField) {
        firstNameField.addEventListener('blur', (e) => {
            e.target.value = normalizeNameInput(e.target.value);
        });
    }
    if (lastNameField) {
        lastNameField.addEventListener('blur', (e) => {
            e.target.value = normalizeNameInput(e.target.value);
        });
    }
    if (childNameField) {
        childNameField.addEventListener('blur', (e) => {
            e.target.value = normalizeNameInput(e.target.value);
        });
    }
    if (phoneField) {
        phoneField.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    }
});
