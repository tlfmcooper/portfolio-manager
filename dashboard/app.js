// Portfolio data
const portfolioData = {
  portfolio: {
    name: "Strategic Multi-Asset Portfolio",
    last_updated: "2025-09-14",
    total_assets: 10,
    total_value: "$1,250,000"
  },
  performance_metrics: {
    annual_return: 0.125,
    annual_volatility: 0.152,
    sharpe_ratio: 1.45,
    sortino_ratio: 1.67,
    max_drawdown: -0.083,
    calmar_ratio: 1.51,
    compound_return: 0.268,
    skewness: -0.124,
    kurtosis: 2.891
  },
  risk_analytics: {
    var_95: -0.021,
    var_99: -0.034,
    cvar: -0.042,
    portfolio_volatility: 0.152,
    semideviation: 0.0934
  },
  asset_allocation: {
    AAPL: 0.15,
    GOOGL: 0.12,
    MSFT: 0.13,
    AMZN: 0.10,
    SPY: 0.20,
    QQQ: 0.10,
    TLT: 0.08,
    GLD: 0.07,
    VNQ: 0.03,
    VEA: 0.02
  },
  efficient_frontier: {
    frontier_points: [
      {risk: 0.08, return: 0.06},
      {risk: 0.10, return: 0.08},
      {risk: 0.12, return: 0.10},
      {risk: 0.14, return: 0.115},
      {risk: 0.16, return: 0.13},
      {risk: 0.18, return: 0.142},
      {risk: 0.20, return: 0.152},
      {risk: 0.22, return: 0.160},
      {risk: 0.25, return: 0.168}
    ],
    special_portfolios: {
      gmv: {risk: 0.12, return: 0.08, name: "Global Minimum Volatility"},
      msr: {risk: 0.16, return: 0.13, name: "Maximum Sharpe Ratio"},
      current: {risk: 0.152, return: 0.125, name: "Current Portfolio"}
    }
  },
  monte_carlo: {
    scenarios: 1000,
    time_horizon: 252,
    initial_value: 1000,
    final_mean: 1125,
    final_std: 152,
    percentile_5: 850,
    percentile_95: 1420,
    success_probability: 0.85,
    simulation_paths: [
      {day: 0, path_1: 1000, path_2: 1000, path_3: 1000, path_4: 1000, path_5: 1000, mean_path: 1000},
      {day: 21, path_1: 1015, path_2: 990, path_3: 1005, path_4: 1020, path_5: 985, mean_path: 1003},
      {day: 42, path_1: 1035, path_2: 975, path_3: 1025, path_4: 1045, path_5: 970, mean_path: 1010},
      {day: 63, path_1: 1060, path_2: 950, path_3: 1055, path_4: 1080, path_5: 945, mean_path: 1018},
      {day: 84, path_1: 1095, path_2: 925, path_3: 1090, path_4: 1125, path_5: 920, mean_path: 1031},
      {day: 105, path_1: 1140, path_2: 890, path_3: 1135, path_4: 1180, path_5: 885, mean_path: 1046},
      {day: 126, path_1: 1195, path_2: 845, path_3: 1190, path_4: 1245, path_5: 840, mean_path: 1063},
      {day: 147, path_1: 1260, path_2: 795, path_3: 1255, path_4: 1320, path_5: 790, mean_path: 1084},
      {day: 168, path_1: 1335, path_2: 740, path_3: 1330, path_4: 1405, path_5: 735, mean_path: 1109},
      {day: 189, path_1: 1420, path_2: 680, path_3: 1415, path_4: 1500, path_5: 675, mean_path: 1138},
      {day: 210, path_1: 1515, path_2: 615, path_3: 1510, path_4: 1605, path_5: 610, mean_path: 1171},
      {day: 231, path_1: 1620, path_2: 545, path_3: 1615, path_4: 1720, path_5: 540, mean_path: 1208},
      {day: 252, path_1: 1735, path_2: 470, path_3: 1730, path_4: 1845, path_5: 465, mean_path: 1249}
    ],
    final_distribution: [
      {range: "400-500", count: 12, percentage: 1.2},
      {range: "500-600", count: 28, percentage: 2.8},
      {range: "600-700", count: 55, percentage: 5.5},
      {range: "700-800", count: 89, percentage: 8.9},
      {range: "800-900", count: 134, percentage: 13.4},
      {range: "900-1000", count: 156, percentage: 15.6},
      {range: "1000-1100", count: 178, percentage: 17.8},
      {range: "1100-1200", count: 145, percentage: 14.5},
      {range: "1200-1300", count: 108, percentage: 10.8},
      {range: "1300-1400", count: 67, percentage: 6.7},
      {range: "1400-1500", count: 28, percentage: 2.8}
    ]
  },
  cppi_analysis: {
    multiplier: 3,
    floor: 0.8,
    initial_value: 1000,
    final_cppi_value: 1180,
    final_buyhold_value: 1125,
    outperformance: 0.049,
    performance_data: [
      {day: 0, cppi_wealth: 1000, buyhold_wealth: 1000, floor_value: 800, risky_allocation: 60, risk_budget: 20},
      {day: 21, cppi_wealth: 1005, buyhold_wealth: 1003, floor_value: 800, risky_allocation: 61.5, risk_budget: 20.5},
      {day: 42, cppi_wealth: 1018, buyhold_wealth: 1010, floor_value: 800, risky_allocation: 65.4, risk_budget: 21.8},
      {day: 63, cppi_wealth: 1035, buyhold_wealth: 1018, floor_value: 800, risky_allocation: 70.5, risk_budget: 23.5},
      {day: 84, cppi_wealth: 1058, buyhold_wealth: 1031, floor_value: 800, risky_allocation: 77.4, risk_budget: 25.8},
      {day: 105, cppi_wealth: 1087, buyhold_wealth: 1046, floor_value: 800, risky_allocation: 86.1, risk_budget: 28.7},
      {day: 126, cppi_wealth: 1122, buyhold_wealth: 1063, floor_value: 800, risky_allocation: 96.6, risk_budget: 32.2},
      {day: 147, cppi_wealth: 1163, buyhold_wealth: 1084, floor_value: 800, risky_allocation: 100, risk_budget: 36.3},
      {day: 168, cppi_wealth: 1172, buyhold_wealth: 1109, floor_value: 800, risky_allocation: 100, risk_budget: 37.2},
      {day: 189, cppi_wealth: 1165, buyhold_wealth: 1138, floor_value: 800, risky_allocation: 100, risk_budget: 36.5},
      {day: 210, cppi_wealth: 1174, buyhold_wealth: 1171, floor_value: 800, risky_allocation: 100, risk_budget: 37.4},
      {day: 231, cppi_wealth: 1179, buyhold_wealth: 1208, floor_value: 800, risky_allocation: 100, risk_budget: 37.9},
      {day: 252, cppi_wealth: 1180, buyhold_wealth: 1125, floor_value: 800, risky_allocation: 100, risk_budget: 38.0}
    ],
    drawdown_data: [
      {day: 0, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 21, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 42, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 63, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 84, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 105, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 126, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 147, cppi_drawdown: 0, buyhold_drawdown: 0},
      {day: 168, cppi_drawdown: -0.8, buyhold_drawdown: -2.3},
      {day: 189, cppi_drawdown: -1.5, buyhold_drawdown: -5.8},
      {day: 210, cppi_drawdown: -0.7, buyhold_drawdown: -3.1},
      {day: 231, cppi_drawdown: -0.3, buyhold_drawdown: 0},
      {day: 252, cppi_drawdown: 0, buyhold_drawdown: -6.9}
    ]
  },
  individual_performance: {
    AAPL: {weight: 0.15, return: 0.14, volatility: 0.24, sharpe: 0.58, contribution: 0.021},
    GOOGL: {weight: 0.12, return: 0.13, volatility: 0.22, sharpe: 0.59, contribution: 0.0156},
    MSFT: {weight: 0.13, return: 0.12, volatility: 0.20, sharpe: 0.60, contribution: 0.0156},
    AMZN: {weight: 0.10, return: 0.11, volatility: 0.26, sharpe: 0.42, contribution: 0.011},
    SPY: {weight: 0.20, return: 0.10, volatility: 0.15, sharpe: 0.67, contribution: 0.020},
    QQQ: {weight: 0.10, return: 0.12, volatility: 0.18, sharpe: 0.67, contribution: 0.012},
    TLT: {weight: 0.08, return: 0.06, volatility: 0.12, sharpe: 0.50, contribution: 0.0048},
    GLD: {weight: 0.07, return: 0.08, volatility: 0.18, sharpe: 0.44, contribution: 0.0056},
    VNQ: {weight: 0.03, return: 0.09, volatility: 0.20, sharpe: 0.45, contribution: 0.0027},
    VEA: {weight: 0.02, return: 0.07, volatility: 0.16, sharpe: 0.44, contribution: 0.0014}
  }
};

// Chart colors
const chartColors = ['#1FB8CD', '#FFC185', '#B4413C', '#ECEBD5', '#5D878F', '#DB4545', '#D2BA4C', '#964325', '#944454', '#13343B'];

// Global chart instances
let charts = {};

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
  initializeNavigation();
  initializeThemeToggle();
  initializeTooltips();
  initializeCharts();
});

// Navigation functionality
function initializeNavigation() {
  const navTabs = document.querySelectorAll('.nav-tab');
  const sections = document.querySelectorAll('.dashboard-section');

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetSection = tab.dataset.section;
      
      // Update active tab
      navTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      // Update active section
      sections.forEach(s => s.classList.remove('active'));
      document.getElementById(targetSection).classList.add('active');
      
      // Refresh charts if needed
      setTimeout(() => {
        Object.values(charts).forEach(chart => {
          if (chart && chart.resize) {
            chart.resize();
          }
        });
      }, 100);
    });
  });
}

// Theme toggle functionality
function initializeThemeToggle() {
  const themeToggle = document.getElementById('themeToggle');
  const currentTheme = document.documentElement.getAttribute('data-color-scheme') || 'light';
  
  updateThemeButton(currentTheme);
  
  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-color-scheme') || 'light';
    const newTheme = current === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-color-scheme', newTheme);
    updateThemeButton(newTheme);
    
    // Update charts for theme change
    setTimeout(() => {
      Object.values(charts).forEach(chart => {
        if (chart && chart.update) {
          chart.update();
        }
      });
    }, 100);
  });
}

function updateThemeButton(theme) {
  const button = document.getElementById('themeToggle');
  if (theme === 'dark') {
    button.innerHTML = '☀️ Light Mode';
  } else {
    button.innerHTML = '🌙 Dark Mode';
  }
}

// Tooltip functionality
function initializeTooltips() {
  const tooltip = document.getElementById('tooltip');
  const metricCards = document.querySelectorAll('.metric-card[data-tooltip]');
  
  metricCards.forEach(card => {
    card.addEventListener('mouseenter', (e) => {
      const tooltipText = card.getAttribute('data-tooltip');
      tooltip.textContent = tooltipText;
      tooltip.classList.remove('hidden');
      updateTooltipPosition(e, tooltip);
    });
    
    card.addEventListener('mousemove', (e) => {
      updateTooltipPosition(e, tooltip);
    });
    
    card.addEventListener('mouseleave', () => {
      tooltip.classList.add('hidden');
    });
  });
}

function updateTooltipPosition(e, tooltip) {
  const x = e.clientX + 10;
  const y = e.clientY - 10;
  
  tooltip.style.left = x + 'px';
  tooltip.style.top = y + 'px';
}

// Chart initialization
function initializeCharts() {
  createPerformanceChart();
  createRiskChart();
  createAllocationChart();
  createEfficientFrontierChart();
  createMonteCarloPathsChart();
  createMonteCarloDistributionChart();
  createCPPIPerformanceChart();
  createCPPIAllocationChart();
  createCPPIRiskBudgetChart();
  createCPPIDrawdownChart();
}

// Performance chart
function createPerformanceChart() {
  const ctx = document.getElementById('performanceChart').getContext('2d');
  const performanceData = portfolioData.individual_performance;
  
  const assets = Object.keys(performanceData);
  const returns = assets.map(asset => performanceData[asset].return * 100);
  const volatilities = assets.map(asset => performanceData[asset].volatility * 100);
  
  charts.performance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: assets,
      datasets: [
        {
          label: 'Annual Return (%)',
          data: returns,
          backgroundColor: chartColors[0],
          borderColor: chartColors[0],
          borderWidth: 1
        },
        {
          label: 'Volatility (%)',
          data: volatilities,
          backgroundColor: chartColors[1],
          borderColor: chartColors[1],
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Individual Asset Performance vs Risk'
        },
        legend: {
          position: 'top'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Percentage (%)'
          }
        }
      }
    }
  });
}

// Risk chart
function createRiskChart() {
  const ctx = document.getElementById('riskChart').getContext('2d');
  const riskData = portfolioData.risk_analytics;
  
  charts.risk = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['VaR 95%', 'VaR 99%', 'CVaR', 'Semideviation'],
      datasets: [{
        data: [
          Math.abs(riskData.var_95 * 100),
          Math.abs(riskData.var_99 * 100),
          Math.abs(riskData.cvar * 100),
          riskData.semideviation * 100
        ],
        backgroundColor: [chartColors[1], chartColors[2], chartColors[3], chartColors[4]],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Risk Metrics Distribution'
        },
        legend: {
          position: 'right'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.label + ': ' + context.parsed.toFixed(2) + '%';
            }
          }
        }
      }
    }
  });
}

// Asset allocation chart
function createAllocationChart() {
  const ctx = document.getElementById('allocationChart').getContext('2d');
  const allocation = portfolioData.asset_allocation;
  
  const assets = Object.keys(allocation);
  const weights = Object.values(allocation).map(w => w * 100);
  
  charts.allocation = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: assets,
      datasets: [{
        data: weights,
        backgroundColor: chartColors,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Asset Allocation'
        },
        legend: {
          position: 'right'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.label + ': ' + context.parsed.toFixed(1) + '%';
            }
          }
        }
      }
    }
  });
}

// Efficient frontier chart
function createEfficientFrontierChart() {
  const ctx = document.getElementById('efficientFrontierChart').getContext('2d');
  const frontierData = portfolioData.efficient_frontier;
  
  const frontierPoints = frontierData.frontier_points.map(p => ({
    x: p.risk * 100,
    y: p.return * 100
  }));
  
  const specialPortfolios = Object.values(frontierData.special_portfolios).map(p => ({
    x: p.risk * 100,
    y: p.return * 100,
    label: p.name
  }));
  
  charts.efficientFrontier = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Efficient Frontier',
          data: frontierPoints,
          borderColor: chartColors[0],
          backgroundColor: chartColors[0],
          showLine: true,
          fill: false,
          pointRadius: 4
        },
        {
          label: 'Current Portfolio',
          data: [specialPortfolios[2]],
          backgroundColor: chartColors[2],
          borderColor: chartColors[2],
          pointRadius: 8,
          pointStyle: 'star'
        },
        {
          label: 'Max Sharpe Ratio',
          data: [specialPortfolios[1]],
          backgroundColor: chartColors[1],
          borderColor: chartColors[1],
          pointRadius: 8,
          pointStyle: 'triangle'
        },
        {
          label: 'Min Volatility',
          data: [specialPortfolios[0]],
          backgroundColor: chartColors[3],
          borderColor: chartColors[3],
          pointRadius: 8,
          pointStyle: 'rect'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Efficient Frontier Analysis'
        },
        legend: {
          position: 'top'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: Risk ${context.parsed.x.toFixed(1)}%, Return ${context.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Risk (Volatility %)'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Expected Return (%)'
          }
        }
      }
    }
  });
}

// Monte Carlo Paths Chart
function createMonteCarloPathsChart() {
  const ctx = document.getElementById('monteCarloPathsChart').getContext('2d');
  const pathData = portfolioData.monte_carlo.simulation_paths;
  
  const days = pathData.map(d => d.day);
  
  charts.monteCarloPaths = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [
        {
          label: 'Path 1',
          data: pathData.map(d => d.path_1),
          borderColor: chartColors[1] + '80',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          borderWidth: 1
        },
        {
          label: 'Path 2',
          data: pathData.map(d => d.path_2),
          borderColor: chartColors[2] + '80',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          borderWidth: 1
        },
        {
          label: 'Path 3',
          data: pathData.map(d => d.path_3),
          borderColor: chartColors[3] + '80',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          borderWidth: 1
        },
        {
          label: 'Path 4',
          data: pathData.map(d => d.path_4),
          borderColor: chartColors[4] + '80',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          borderWidth: 1
        },
        {
          label: 'Path 5',
          data: pathData.map(d => d.path_5),
          borderColor: chartColors[5] + '80',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          borderWidth: 1
        },
        {
          label: 'Mean Path',
          data: pathData.map(d => d.mean_path),
          borderColor: chartColors[0],
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          pointRadius: 2,
          borderWidth: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            title: function(tooltipItems) {
              return `Day ${tooltipItems[0].label}`;
            },
            label: function(context) {
              return `${context.dataset.label}: $${context.parsed.y.toFixed(0)}K`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Trading Days'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Portfolio Value ($K)'
          }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  });
}

// Monte Carlo Distribution Chart
function createMonteCarloDistributionChart() {
  const ctx = document.getElementById('monteCarloDistributionChart').getContext('2d');
  const distributionData = portfolioData.monte_carlo.final_distribution;
  
  const labels = distributionData.map(d => d.range);
  const counts = distributionData.map(d => d.count);
  
  charts.monteCarloDistribution = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Number of Scenarios',
        data: counts,
        backgroundColor: chartColors[0],
        borderColor: chartColors[0],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            title: function(tooltipItems) {
              return `Final Value Range: $${tooltipItems[0].label}K`;
            },
            label: function(context) {
              const percentage = distributionData[context.dataIndex].percentage;
              return `${context.parsed.y} scenarios (${percentage}%)`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Final Portfolio Value Range ($K)'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Number of Scenarios'
          },
          beginAtZero: true
        }
      }
    }
  });
}

// CPPI Performance Chart
function createCPPIPerformanceChart() {
  const ctx = document.getElementById('cppiPerformanceChart').getContext('2d');
  const performanceData = portfolioData.cppi_analysis.performance_data;
  
  const days = performanceData.map(d => d.day);
  const cppiWealth = performanceData.map(d => d.cppi_wealth);
  const buyholdWealth = performanceData.map(d => d.buyhold_wealth);
  const floorValues = performanceData.map(d => d.floor_value);
  
  charts.cppiPerformance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [
        {
          label: 'CPPI Strategy',
          data: cppiWealth,
          borderColor: chartColors[0],
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          borderWidth: 3
        },
        {
          label: 'Buy & Hold',
          data: buyholdWealth,
          borderColor: chartColors[1],
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.1,
          borderWidth: 2
        },
        {
          label: 'Floor Protection',
          data: floorValues,
          borderColor: chartColors[2],
          backgroundColor: 'transparent',
          fill: false,
          tension: 0,
          borderWidth: 2,
          borderDash: [5, 5]
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            title: function(tooltipItems) {
              return `Day ${tooltipItems[0].label}`;
            },
            label: function(context) {
              return `${context.dataset.label}: $${context.parsed.y.toFixed(0)}K`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Trading Days'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Portfolio Value ($K)'
          }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  });
}

// CPPI Allocation Chart
function createCPPIAllocationChart() {
  const ctx = document.getElementById('cppiAllocationChart').getContext('2d');
  const performanceData = portfolioData.cppi_analysis.performance_data;
  
  const days = performanceData.map(d => d.day);
  const riskyAllocation = performanceData.map(d => d.risky_allocation);
  const safeAllocation = riskyAllocation.map(r => 100 - r);
  
  charts.cppiAllocation = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [
        {
          label: 'Risky Assets (%)',
          data: riskyAllocation,
          borderColor: chartColors[0],
          backgroundColor: chartColors[0] + '40',
          fill: 'origin',
          tension: 0.1
        },
        {
          label: 'Safe Assets (%)',
          data: safeAllocation,
          borderColor: chartColors[3],
          backgroundColor: chartColors[3] + '40',
          fill: '-1',
          tension: 0.1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            title: function(tooltipItems) {
              return `Day ${tooltipItems[0].label}`;
            },
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Trading Days'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Allocation Percentage (%)'
          },
          min: 0,
          max: 100,
          stacked: true
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  });
}

// CPPI Risk Budget Chart (Fixed)
function createCPPIRiskBudgetChart() {
  const ctx = document.getElementById('cppiRiskBudgetChart').getContext('2d');
  const performanceData = portfolioData.cppi_analysis.performance_data;
  
  const days = performanceData.map(d => d.day);
  const riskBudget = performanceData.map(d => d.risk_budget);
  
  charts.cppiRiskBudget = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [{
        label: 'Risk Budget (Cushion)',
        data: riskBudget,
        borderColor: chartColors[4],
        backgroundColor: chartColors[4] + '40',
        fill: 'origin',
        tension: 0.1,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            title: function(tooltipItems) {
              return `Day ${tooltipItems[0].label}`;
            },
            label: function(context) {
              return `Risk Budget: ${context.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Trading Days'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Risk Budget (% above floor)'
          },
          beginAtZero: true
        }
      }
    }
  });
}

// CPPI Drawdown Chart (Fixed)
function createCPPIDrawdownChart() {
  const ctx = document.getElementById('cppiDrawdownChart').getContext('2d');
  const drawdownData = portfolioData.cppi_analysis.drawdown_data;
  
  const days = drawdownData.map(d => d.day);
  const cppiDrawdowns = drawdownData.map(d => d.cppi_drawdown);
  const buyholdDrawdowns = drawdownData.map(d => d.buyhold_drawdown);
  
  charts.cppiDrawdown = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [
        {
          label: 'CPPI Drawdown',
          data: cppiDrawdowns,
          borderColor: chartColors[0],
          backgroundColor: chartColors[0] + '40',
          fill: 'origin',
          tension: 0.1,
          borderWidth: 2
        },
        {
          label: 'Buy & Hold Drawdown',
          data: buyholdDrawdowns,
          borderColor: chartColors[1],
          backgroundColor: chartColors[1] + '40',
          fill: 'origin',
          tension: 0.1,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            title: function(tooltipItems) {
              return `Day ${tooltipItems[0].label}`;
            },
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Trading Days'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Drawdown (%)'
          },
          max: 1,
          min: -8
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  });
}