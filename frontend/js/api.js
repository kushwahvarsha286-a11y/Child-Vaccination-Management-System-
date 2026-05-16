const API_BASE_URL = 'http://127.0.0.1:5000/api';

const getHeaders = ({ json = false } = {}) => {
    const headers = {};
    if (json) {
        headers['Content-Type'] = 'application/json';
    }
    const token = localStorage.getItem('userToken');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
};

// API Calls
const api = {
    // ===== AUTH / PROFILE =====
    login: async (credentials) => {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials)
        });
        return response.json();
    },
    
    signupParent: async (data) => {
        const response = await fetch(`${API_BASE_URL}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    registerStaff: async (data) => {
        const response = await fetch(`${API_BASE_URL}/auth/register/staff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    // Admin-only: create staff via /auth/signup/staff
    signupStaff: async (data) => {
        const response = await fetch(`${API_BASE_URL}/auth/signup/staff`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },

    getProfile: async () => {
        const response = await fetch(`${API_BASE_URL}/auth/profile`, { headers: getHeaders() });
        return response.json();
    },

    updateProfile: async (data) => {
        const response = await fetch(`${API_BASE_URL}/auth/profile`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },

    // ===== CHILDREN =====
    getChildren: async () => {
        const token = localStorage.getItem('userToken');
        if (!token) {
            console.error('Children fetch aborted: missing authentication token');
            throw new Error('Authentication required to load children');
        }

        const response = await fetch(`${API_BASE_URL}/children`, { headers: getHeaders() });
        if (!response.ok) {
            const errorText = await response.text();
            let errorData = null;
            try {
                errorData = JSON.parse(errorText);
            } catch (err) {
                // ignore parse error
            }
            const errorMessage = errorData?.error || response.statusText || 'Failed to fetch children';
            console.error('Failed to fetch children:', response.status, errorMessage, errorData);
            throw new Error(errorMessage);
        }

        return response.json();
    },
    
    getChild: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/children/${childId}`, { headers: getHeaders() });
        if (!response.ok) {
            const errorText = await response.text();
            let errorData = null;
            try {
                errorData = JSON.parse(errorText);
            } catch (err) {
                // ignore parse error
            }
            const errorMessage = errorData?.error || response.statusText || 'Failed to fetch child';
            console.error('Failed to fetch child:', response.status, errorMessage, errorData);
            throw new Error(errorMessage);
        }
        return response.json();
    },
    
    createChild: async (data) => {
        const response = await fetch(`${API_BASE_URL}/children`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    updateChild: async (childId, data) => {
        const response = await fetch(`${API_BASE_URL}/children/${childId}`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    deleteChild: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/children/${childId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },
    
    // ===== VACCINATIONS =====
    getVaccinations: async () => {
        const response = await fetch(`${API_BASE_URL}/vaccinations/`, { headers: getHeaders() });
        return response.json();
    },
    
    getChildVaccinations: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/vaccinations/child/${childId}`, { headers: getHeaders() });
        return response.json();
    },
    
    getVaccines: async () => {
        const response = await fetch(`${API_BASE_URL}/vaccines/stock`, { headers: getHeaders() });
        return response.json();
    },
    
    createVaccination: async (data) => {
        const response = await fetch(`${API_BASE_URL}/vaccinations/`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    updateVaccination: async (vaccinationId, data) => {
        const response = await fetch(`${API_BASE_URL}/vaccinations/${vaccinationId}`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    deleteVaccination: async (vaccinationId) => {
        const response = await fetch(`${API_BASE_URL}/vaccinations/${vaccinationId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },
    
    // ===== APPOINTMENTS =====
    getAppointments: async () => {
        const response = await fetch(`${API_BASE_URL}/appointments/`, { headers: getHeaders() });
        return response.json();
    },
    
    getChildAppointments: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/appointments/child/${childId}`, { headers: getHeaders() });
        return response.json();
    },
    
    createAppointment: async (data) => {
        const response = await fetch(`${API_BASE_URL}/appointments/`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    updateAppointment: async (appointmentId, data) => {
        const response = await fetch(`${API_BASE_URL}/appointments/${appointmentId}`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    deleteAppointment: async (appointmentId) => {
        const response = await fetch(`${API_BASE_URL}/appointments/${appointmentId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },
    
    // ===== PROVIDERS =====
    getProviders: async () => {
        const response = await fetch(`${API_BASE_URL}/providers/`, { headers: getHeaders() });
        return response.json();
    },
    
    createProvider: async (data) => {
        const response = await fetch(`${API_BASE_URL}/providers/`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    updateProvider: async (providerId, data) => {
        const response = await fetch(`${API_BASE_URL}/providers/${providerId}`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    deleteProvider: async (providerId) => {
        const response = await fetch(`${API_BASE_URL}/providers/${providerId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },
    
    // ===== NOTIFICATIONS =====
    getNotifications: async () => {
        const response = await fetch(`${API_BASE_URL}/notifications/`, { headers: getHeaders() });
        return response.json();
    },
    
    getChildNotifications: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/notifications/child/${childId}`, { headers: getHeaders() });
        return response.json();
    },
    
    markNotificationAsRead: async (notificationId) => {
        const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}/mark-read`, {
            method: 'PUT',
            headers: getHeaders()
        });
        return response.json();
    },
    
    deleteNotification: async (notificationId) => {
        const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },

    // ===== DASHBOARD & STATS =====
    getDashboardStats: async () => {
        const response = await fetch(`${API_BASE_URL}/dashboard/stats`, { headers: getHeaders() });
        return response.json();
    },

    // ===== VACCINE STOCK =====
    getVaccineStock: async () => {
        const response = await fetch(`${API_BASE_URL}/vaccines/stock`, { headers: getHeaders() });
        return response.json();
    },

    updateVaccineStock: async (vaccineId, data) => {
        const response = await fetch(`${API_BASE_URL}/vaccines/stock/${vaccineId}`, {
            method: 'PUT',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },

    // ===== ADMIN – USER & STAFF MANAGEMENT =====
    adminGetUsers: async () => {
        const response = await fetch(`${API_BASE_URL}/admin/users`, { headers: getHeaders() });
        return response.json();
    },

    adminGetStaff: async () => {
        const response = await fetch(`${API_BASE_URL}/admin/staff`, { headers: getHeaders() });
        return response.json();
    },

    adminCreateStaff: async (data) => {
        const response = await fetch(`${API_BASE_URL}/admin/staff`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify(data)
        });
        return response.json();
    },

    adminDeleteStaff: async (staffId) => {
        const response = await fetch(`${API_BASE_URL}/admin/staff/${staffId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },

    adminDeleteUser: async (userId) => {
        const response = await fetch(`${API_BASE_URL}/admin/user/${userId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return response.json();
    },

    // Staff Approval Workflow
    adminGetPendingStaff: async () => {
        const response = await fetch(`${API_BASE_URL}/admin/staff/pending`, { headers: getHeaders() });
        return response.json();
    },

    adminApproveStaff: async (staffId) => {
        const response = await fetch(`${API_BASE_URL}/admin/staff/${staffId}/approve`, {
            method: 'POST',
            headers: getHeaders()
        });
        return response.json();
    },

    adminRejectStaff: async (staffId, reason) => {
        const response = await fetch(`${API_BASE_URL}/admin/staff/${staffId}/reject`, {
            method: 'POST',
            headers: getHeaders({ json: true }),
            body: JSON.stringify({ reason })
        });
        return response.json();
    },

    adminGetSummary: async () => {
        const response = await fetch(`${API_BASE_URL}/admin/summary`, { headers: getHeaders() });
        return response.json();
    },

    adminGetChildren: async () => {
        const response = await fetch(`${API_BASE_URL}/admin/children`, { headers: getHeaders() });
        return response.json();
    },

    // ===== REPORTS / PDF CERTIFICATES =====
    generateReport: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/reports/generate/child/${childId}`, {
            method: 'POST',
            headers: getHeaders()
        });
        return response.json();
    },

    downloadReport: async (reportId) => {
        const token = localStorage.getItem('userToken');
        const response = await fetch(`${API_BASE_URL}/reports/download/${reportId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to download');
        }
        return response.blob();
    },

    getChildReports: async (childId) => {
        const response = await fetch(`${API_BASE_URL}/reports/child/${childId}`, { headers: getHeaders() });
        return response.json();
    }
};
