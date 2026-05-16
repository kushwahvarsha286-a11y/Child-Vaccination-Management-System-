// Utility functions
const utils = {
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    },
    
    formatDateTime: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    calculateAge: (dateOfBirth) => {
        if (!dateOfBirth) return 'N/A';
        const today = new Date();
        const birthDate = new Date(dateOfBirth);
        let years = today.getFullYear() - birthDate.getFullYear();
        let months = today.getMonth() - birthDate.getMonth();
        let days = today.getDate() - birthDate.getDate();

        if (days < 0) {
            months--;
            // Add days from the previous month
            const prevMonth = new Date(today.getFullYear(), today.getMonth(), 0);
            days += prevMonth.getDate();
        }

        if (months < 0) {
            years--;
            months += 12;
        }

        if (years === 0 && months === 0) {
            return `${days} days`;
        } else if (years === 0) {
            return `${months} months${days > 0 ? `, ${days} days` : ''}`;
        } else {
            return `${years} years${months > 0 ? `, ${months} months` : ''}`;
        }
    },
    
    // ===== MODERN POPUP ALERTS (SweetAlert2) =====

    // Base SweetAlert2 config for a dark-themed, polished look
    _swalBase: {
        background: '#1e293b',
        color: '#f1f5f9',
        backdrop: 'rgba(0,0,0,0.65)',
        customClass: {
            popup: 'vaccicare-swal-popup',
            title: 'vaccicare-swal-title',
            htmlContainer: 'vaccicare-swal-html',
            confirmButton: 'vaccicare-swal-confirm',
            cancelButton: 'vaccicare-swal-cancel',
            timerProgressBar: 'vaccicare-swal-timer'
        }
    },

    showAlert: (message, type = 'success') => {
        const typeMap = {
            success: { icon: 'success', title: 'Success', confirmButtonColor: '#10b981' },
            error:   { icon: 'error',   title: 'Error',   confirmButtonColor: '#ef4444' },
            warning: { icon: 'warning', title: 'Warning', confirmButtonColor: '#f59e0b' },
            info:    { icon: 'info',    title: 'Info',    confirmButtonColor: '#3b82f6' }
        };
        const t = typeMap[type] || typeMap.success;
        Swal.fire({
            ...utils._swalBase,
            icon: t.icon,
            title: t.title,
            html: message,
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
    },

    showError: (message) => {
        Swal.fire({
            ...utils._swalBase,
            icon: 'error',
            title: 'Something went wrong',
            html: `<span style="color:#fca5a5">${message}</span>`,
            showConfirmButton: true,
            confirmButtonText: '<i class="fas fa-times"></i> Dismiss',
            confirmButtonColor: '#ef4444',
            allowOutsideClick: true,
            showClass: { popup: 'animate__animated animate__shakeX' }
        });
    },

    showWarning: (message) => {
        Swal.fire({
            ...utils._swalBase,
            icon: 'warning',
            title: 'Warning',
            html: `<span style="color:#fde68a">${message}</span>`,
            showConfirmButton: true,
            confirmButtonText: '<i class="fas fa-check"></i> Got it',
            confirmButtonColor: '#f59e0b',
            allowOutsideClick: true
        });
    },

    showInfo: (message) => {
        Swal.fire({
            ...utils._swalBase,
            icon: 'info',
            title: 'Information',
            html: `<span style="color:#bfdbfe">${message}</span>`,
            showConfirmButton: true,
            confirmButtonText: '<i class="fas fa-check"></i> OK',
            confirmButtonColor: '#3b82f6',
            allowOutsideClick: true
        });
    },

    showSuccess: (message) => {
        Swal.fire({
            ...utils._swalBase,
            icon: 'success',
            title: 'Success!',
            html: `<span style="color:#a7f3d0">${message}</span>`,
            showConfirmButton: false,
            timer: 2800,
            timerProgressBar: true
        });
    },

    showConfirm: async (title, message, confirmButtonText = 'Yes, Delete', cancelButtonText = 'Cancel', isDangerous = false) => {
        return await Swal.fire({
            ...utils._swalBase,
            icon: isDangerous ? 'warning' : 'question',
            title: title,
            html: `<span style="color:#cbd5e1">${message}</span>`,
            showCancelButton: true,
            confirmButtonText: confirmButtonText,
            cancelButtonText: cancelButtonText,
            confirmButtonColor: isDangerous ? '#ef4444' : '#3b82f6',
            cancelButtonColor: '#475569',
            allowOutsideClick: false,
            focusCancel: isDangerous,
            reverseButtons: isDangerous
        });
    },

    // Toast notification (top-right, auto-closes) — lightweight, non-blocking
    showToast: (message, type = 'success') => {
        const iconColors = {
            success: '#10b981',
            error:   '#ef4444',
            warning: '#f59e0b',
            info:    '#3b82f6'
        };

        const Toast = Swal.mixin({
            toast: true,
            position: 'top-right',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            background: '#1e293b',
            color: '#f1f5f9',
            iconColor: iconColors[type] || iconColors.success,
            customClass: { popup: 'vaccicare-toast' },
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });

        Toast.fire({ icon: type, title: message });
    },

    showLoading: (elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add('loading');
        }
    },
    
    hideLoading: (elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('loading');
        }
    },
    
    openModal: (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
        }
    },
    
    closeModal: (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
        }
    },
    
    resetForm: (formId) => {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
        }
    },
    
    clearElement: (elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '';
        }
    },
    
    isEmpty: (value) => {
        return value === null || value === undefined || value === '';
    },
    
    getFormData: (formId) => {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }
};
