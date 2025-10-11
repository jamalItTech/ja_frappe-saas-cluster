// الإعدادات
const API_BASE_URL = 'http://5000--main--fuchsia-heron-44-copy--jamal.coder.ittech-ye.net';

// تطبيقات النظام
const AVAILABLE_APPS = [
    { 
        id: 'erpnext', 
        name: 'ERPNext', 
        description: 'نظام تخطيط الموارد المتكامل - إدارة الحسابات والمخزون والمبيعات', 
        icon: '📊',
        features: ['المحاسبة', 'المخزون', 'المبيعات', 'المشتريات']
    },
    { 
        id: 'hrms', 
        name: 'HRMS', 
        description: 'نظام إدارة الموارد البشرية - إدارة الموظفين والرواتب والحضور', 
        icon: '👥',
        features: ['إدارة الموظفين', 'الرواتب', 'الحضور', 'التقييمات']
    },
    { 
        id: 'crm', 
        name: 'CRM', 
        description: 'نظام إدارة علاقات العملاء - متابعة العملاء والمبيعات والتسويق', 
        icon: '🤝',
        features: ['إدارة العملاء', 'المبيعات', 'التسويق', 'الدعم']
    },
    { 
        id: 'lms', 
        name: 'LMS', 
        description: 'نظام إدارة التعلم - إنشاء وإدارة الدورات التدريبية', 
        icon: '🎓',
        features: ['الدورات', 'الاختبارات', 'الشهادات', 'التقارير']
    },
    { 
        id: 'website', 
        name: 'Website', 
        description: 'منشئ مواقع الويب - إنشاء موقع شركتك بسهولة', 
        icon: '🌐',
        features: ['منشئ المواقع', 'التصميم', 'المحتوى', 'SEO']
    }
];

// وظائف التنقل
function startTrial() {
    window.location.href = 'select-apps.html';
}

function bookDemo() {
    window.location.href = 'book-demo.html';
}

function goHome() {
    window.location.href = 'index.html';
}

// وظائف المساعدة
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1000; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentElement) {
            alertDiv.remove();
        }
    }, 5000);
}

// إضافة عنصر التحميل للصفحة
document.addEventListener('DOMContentLoaded', function() {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'loadingOverlay';
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">جاري التحميل...</span>
            </div>
            <div class="mt-2">جاري المعالجة...</div>
        </div>
    `;
    document.body.appendChild(loadingOverlay);
});
