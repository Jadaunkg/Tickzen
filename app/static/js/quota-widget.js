/**
 * Quota Widget JavaScript
 * Manages quota display and real-time updates
 */

class QuotaWidget {
    constructor(containerId = 'quota-widget') {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn('Quota widget container not found');
            return;
        }
        
        this.quotaData = null;
        this.refreshInterval = null;
        this.init();
    }
    
    async init() {
        console.log('Initializing quota widget...');
        await this.fetchQuotaStatus();
        this.render();
        this.startAutoRefresh();
    }
    
    async fetchQuotaStatus() {
        try {
            this.showLoading(true);
            const response = await fetch('/api/quota/status');
            
            if (!response.ok) {
                if (response.status === 401) {
                    console.log('User not logged in, hiding quota widget');
                    this.container.style.display = 'none';
                    return null;
                }
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.quotaData = data;
            console.log('Quota status fetched:', data);
            return data;
            
        } catch (error) {
            console.error('Failed to fetch quota status:', error);
            this.showError();
            return null;
        } finally {
            this.showLoading(false);
        }
    }
    
    render() {
        if (!this.quotaData || !this.container) return;
        
        const { stock_reports, plan_type } = this.quotaData;
        
        // Update usage numbers
        const usedEl = document.getElementById('quota-used');
        const limitEl = document.getElementById('quota-limit');
        const remainingEl = document.getElementById('quota-remaining-text');
        
        if (usedEl) usedEl.textContent = stock_reports.used || 0;
        if (limitEl) {
            limitEl.textContent = stock_reports.unlimited ? '∞' : (stock_reports.limit || 0);
        }
        
        // Update remaining text
        if (remainingEl) {
            if (stock_reports.unlimited) {
                remainingEl.textContent = 'Unlimited reports available';
                remainingEl.style.color = '#27ae60';
            } else {
                const remaining = stock_reports.remaining || 0;
                remainingEl.textContent = `${remaining} report${remaining !== 1 ? 's' : ''} remaining`;
                
                // Color code based on remaining
                if (remaining === 0) {
                    remainingEl.style.color = '#e74c3c';
                } else if (remaining <= 2) {
                    remainingEl.style.color = '#e67e22';
                } else {
                    remainingEl.style.color = '#7f8c8d';
                }
            }
        }
        
        // Update progress bar
        const progressBar = document.getElementById('quota-progress-fill');
        if (progressBar) {
            const percentage = stock_reports.unlimited 
                ? 100 
                : Math.min(100, (stock_reports.used / stock_reports.limit) * 100);
            
            progressBar.style.width = `${percentage}%`;
            
            // Remove all status classes
            progressBar.classList.remove('warning', 'danger');
            
            // Add appropriate class based on usage
            if (percentage >= 90) {
                progressBar.classList.add('danger');
            } else if (percentage >= 75) {
                progressBar.classList.add('warning');
            }
        }
        
        // Update plan badge
        const planBadge = document.getElementById('quota-plan-badge');
        if (planBadge) {
            planBadge.textContent = this.formatPlanName(plan_type);
            planBadge.className = `quota-plan-badge ${plan_type}`;
        }
        
        // Update reset date
        const resetDateEl = document.getElementById('quota-reset-date');
        if (resetDateEl && stock_reports.period_end) {
            const resetDate = new Date(stock_reports.period_end);
            resetDateEl.textContent = resetDate.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        }
        
        // Show/hide upgrade link
        const upgradeLink = document.getElementById('quota-upgrade-link');
        if (upgradeLink) {
            // Show upgrade link if not unlimited and not enterprise
            const showUpgrade = !stock_reports.unlimited && 
                              plan_type !== 'enterprise' &&
                              (stock_reports.remaining || 0) <= 5;
            upgradeLink.style.display = showUpgrade ? 'inline-block' : 'none';
        }
    }
    
    formatPlanName(planType) {
        const names = {
            'free': 'Free Plan',
            'pro': 'Pro Plan',
            'pro_plus': 'Pro+ Plan',
            'enterprise': 'Enterprise'
        };
        return names[planType] || planType.toUpperCase();
    }
    
    showLoading(show) {
        const loadingEl = document.getElementById('quota-loading');
        if (loadingEl) {
            loadingEl.style.display = show ? 'flex' : 'none';
        }
    }
    
    showError() {
        const remainingEl = document.getElementById('quota-remaining-text');
        if (remainingEl) {
            remainingEl.textContent = 'Failed to load quota status';
            remainingEl.style.color = '#e74c3c';
        }
    }
    
    startAutoRefresh() {
        // Refresh every 60 seconds
        this.refreshInterval = setInterval(async () => {
            await this.fetchQuotaStatus();
            this.render();
        }, 60000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    async refresh() {
        await this.fetchQuotaStatus();
        this.render();
    }
    
    destroy() {
        this.stopAutoRefresh();
        this.quotaData = null;
    }
}

// Initialize quota widget when DOM is ready
let quotaWidgetInstance = null;

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('quota-widget')) {
        quotaWidgetInstance = new QuotaWidget('quota-widget');
        
        // Make it globally accessible
        window.quotaWidget = quotaWidgetInstance;
        
        console.log('Quota widget initialized and available as window.quotaWidget');
    }
});

// Listen for custom quota events
document.addEventListener('quotaUpdated', function() {
    if (window.quotaWidget) {
        console.log('Quota updated event received, refreshing widget...');
        window.quotaWidget.refresh();
    }
});

// Refresh quota after successful report generation
document.addEventListener('reportGenerated', function() {
    if (window.quotaWidget) {
        console.log('Report generated, refreshing quota widget...');
        setTimeout(() => {
            window.quotaWidget.refresh();
        }, 1000); // Small delay to ensure backend has updated
    }
});
