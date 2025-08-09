// Training Center CRM - Charts and Analytics

// Global chart instances
let pipelineChart, revenueChart, conversionChart, courseChart;

// Initialize all dashboard charts
function initializeDashboardCharts() {
    initializePipelineChart();
    initializeRevenueChart();
    initializeConversionChart();
    initializeCourseChart();
}

// Pipeline Funnel Chart
function initializePipelineChart() {
    const ctx = document.getElementById('pipelineChart');
    if (!ctx) return;

    fetch('/api/pipeline/data')
        .then(response => response.json())
        .then(data => {
            const statuses = ['New', 'Contacted', 'Interested', 'Quoted', 'Converted'];
            const counts = statuses.map(status => data[status]?.count || 0);
            const values = statuses.map(status => data[status]?.total_value || 0);

            pipelineChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: statuses,
                    datasets: [{
                        label: 'Lead Count',
                        data: counts,
                        backgroundColor: [
                            '#3498db', // New - Blue
                            '#f39c12', // Contacted - Orange
                            '#e67e22', // Interested - Dark Orange
                            '#9b59b6', // Quoted - Purple
                            '#27ae60'  // Converted - Green
                        ],
                        borderWidth: 0,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Sales Pipeline Overview',
                            font: { size: 16, weight: 'bold' }
                        },
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                afterLabel: function(context) {
                                    const index = context.dataIndex;
                                    const value = values[index];
                                    return value > 0 ? `Value: $${value.toLocaleString()}` : '';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    }
                }
            });
        })
        .catch(error => console.error('Error loading pipeline data:', error));
}

// Monthly Revenue Chart
function initializeRevenueChart() {
    const ctx = document.getElementById('revenueChart');
    if (!ctx) return;

    // Sample data - in real app, fetch from API
    const monthlyRevenue = [
        { month: '2024-01', revenue: 15000 },
        { month: '2024-02', revenue: 18000 },
        { month: '2024-03', revenue: 22000 },
        { month: '2024-04', revenue: 25000 },
        { month: '2024-05', revenue: 28000 },
        { month: '2024-06', revenue: 32000 }
    ];

    const labels = monthlyRevenue.map(item => {
        const date = new Date(item.month + '-01');
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    });
    const data = monthlyRevenue.map(item => item.revenue);

    revenueChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Revenue',
                data: data,
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3498db',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Monthly Revenue Trend',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Conversion Rate Chart
function initializeConversionChart() {
    const ctx = document.getElementById('conversionChart');
    if (!ctx) return;

    // Sample conversion data by source
    const conversionData = [
        { source: 'Website', total: 100, converted: 15 },
        { source: 'Social Media', total: 80, converted: 20 },
        { source: 'Referral', total: 60, converted: 25 },
        { source: 'Advertisement', total: 120, converted: 18 },
        { source: 'Walk-in', total: 40, converted: 30 }
    ];

    const labels = conversionData.map(item => item.source);
    const rates = conversionData.map(item => (item.converted / item.total * 100).toFixed(1));

    conversionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Conversion Rate (%)',
                data: rates,
                backgroundColor: [
                    '#3498db',
                    '#e74c3c',
                    '#27ae60',
                    '#f39c12',
                    '#9b59b6'
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Conversion Rate by Source',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const item = conversionData[index];
                            return `${context.label}: ${context.parsed}% (${item.converted}/${item.total})`;
                        }
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Course Popularity Chart
function initializeCourseChart() {
    const ctx = document.getElementById('courseChart');
    if (!ctx) return;

    // Sample course enrollment data
    const courseData = [
        { name: 'Web Development', enrollments: 45 },
        { name: 'Data Science', enrollments: 38 },
        { name: 'Digital Marketing', enrollments: 32 },
        { name: 'Graphic Design', enrollments: 28 },
        { name: 'Mobile Development', enrollments: 25 }
    ];

    const labels = courseData.map(item => item.name);
    const data = courseData.map(item => item.enrollments);

    courseChart = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Enrollments',
                data: data,
                backgroundColor: [
                    '#3498db',
                    '#27ae60',
                    '#f39c12',
                    '#e74c3c',
                    '#9b59b6'
                ],
                borderWidth: 0,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                title: {
                    display: true,
                    text: 'Course Popularity',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Real-time chart updates
function updateCharts() {
    if (pipelineChart) {
        fetch('/api/pipeline/data')
            .then(response => response.json())
            .then(data => {
                const statuses = ['New', 'Contacted', 'Interested', 'Quoted', 'Converted'];
                const counts = statuses.map(status => data[status]?.count || 0);
                
                pipelineChart.data.datasets[0].data = counts;
                pipelineChart.update('none');
            });
    }
}

// Analytics for reports page
function initializeReportsCharts() {
    initializeMonthlyLeadsChart();
    initializeSourcePerformanceChart();
    initializeRevenueBreakdownChart();
}

function initializeMonthlyLeadsChart() {
    const ctx = document.getElementById('monthlyLeadsChart');
    if (!ctx) return;

    // Sample data - replace with actual API call
    const monthlyLeads = [
        { month: '2024-01', leads: 25, converted: 6 },
        { month: '2024-02', leads: 32, converted: 8 },
        { month: '2024-03', leads: 28, converted: 7 },
        { month: '2024-04', leads: 35, converted: 9 },
        { month: '2024-05', leads: 42, converted: 12 },
        { month: '2024-06', leads: 38, converted: 10 }
    ];

    const labels = monthlyLeads.map(item => {
        const date = new Date(item.month + '-01');
        return date.toLocaleDateString('en-US', { month: 'short' });
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Leads',
                data: monthlyLeads.map(item => item.leads),
                backgroundColor: 'rgba(52, 152, 219, 0.8)',
                borderRadius: 6
            }, {
                label: 'Converted',
                data: monthlyLeads.map(item => item.converted),
                backgroundColor: 'rgba(39, 174, 96, 0.8)',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Monthly Lead Generation & Conversion',
                    font: { size: 16, weight: 'bold' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function initializeSourcePerformanceChart() {
    const ctx = document.getElementById('sourcePerformanceChart');
    if (!ctx) return;

    const sourceData = [
        { source: 'Website', leads: 45, cost: 500, revenue: 6750 },
        { source: 'Social Media', leads: 32, cost: 300, revenue: 6400 },
        { source: 'Google Ads', leads: 28, cost: 800, revenue: 5040 },
        { source: 'Referral', leads: 22, cost: 100, revenue: 5500 },
        { source: 'Direct', leads: 18, cost: 0, revenue: 5400 }
    ];

    const labels = sourceData.map(item => item.source);
    const roi = sourceData.map(item => 
        item.cost > 0 ? ((item.revenue - item.cost) / item.cost * 100).toFixed(1) : 100
    );

    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'ROI (%)',
                data: roi,
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                borderWidth: 2,
                pointBackgroundColor: '#3498db',
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Lead Source Performance (ROI)',
                    font: { size: 16, weight: 'bold' }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: Math.max(...roi) + 50
                }
            }
        }
    });
}

function initializeRevenueBreakdownChart() {
    const ctx = document.getElementById('revenueBreakdownChart');
    if (!ctx) return;

    const revenueData = [
        { category: 'Individual Courses', amount: 45000 },
        { category: 'Corporate Training', amount: 32000 },
        { category: 'Online Courses', amount: 18000 },
        { category: 'Workshops', amount: 12000 },
        { category: 'Certifications', amount: 8000 }
    ];

    const labels = revenueData.map(item => item.category);
    const amounts = revenueData.map(item => item.amount);

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: amounts,
                backgroundColor: [
                    '#3498db',
                    '#27ae60',
                    '#f39c12',
                    '#e74c3c',
                    '#9b59b6'
                ],
                borderWidth: 0,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Revenue Breakdown by Category',
                    font: { size: 16, weight: 'bold' }
                },
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: $${context.parsed.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Update charts periodically
setInterval(updateCharts, 30000); // Update every 30 seconds

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Delay chart initialization to ensure Chart.js is loaded
    setTimeout(() => {
        if (typeof Chart !== 'undefined') {
            initializeDashboardCharts();
            
            // Initialize reports charts if on reports page
            if (window.location.pathname.includes('reports')) {
                initializeReportsCharts();
            }
        }
    }, 500);
});
