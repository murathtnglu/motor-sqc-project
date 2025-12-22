// React Component Library - Modüler yapı için ayrı dosya
// Bu dosya index.html tarafından import edilebilir

// ==================== SHARED COMPONENTS ====================

// Loading Spinner Component
const LoadingSpinner = () => (
    <div className="flex justify-center items-center min-h-screen">
        <div className="relative">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            <div className="absolute top-0 left-0 h-32 w-32 flex items-center justify-center">
                <span className="text-blue-600 font-semibold">Yükleniyor...</span>
            </div>
        </div>
    </div>
);

// Error Boundary Component
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }
    
    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }
    
    componentDidCatch(error, errorInfo) {
        console.error('Dashboard Error:', error, errorInfo);
    }
    
    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-red-50">
                    <div className="text-center p-8">
                        <h1 className="text-4xl font-bold text-red-600 mb-4">⚠️ Hata Oluştu</h1>
                        <p className="text-gray-700 mb-4">Dashboard yüklenirken bir hata oluştu.</p>
                        <button 
                            onClick={() => window.location.reload()}
                            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Sayfayı Yenile
                        </button>
                    </div>
                </div>
            );
        }
        
        return this.props.children;
    }
}

// Data Fetcher Hook
const useDataFetch = (url, refreshInterval = null) => {
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    
    React.useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await fetch(url);
                if (!response.ok) throw new Error('Veri yüklenemedi');
                const jsonData = await response.json();
                setData(jsonData);
                setError(null);
            } catch (err) {
                setError(err.message);
                // Fallback to mock data if fetch fails
                setData(MOCK_DATA);
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
        
        if (refreshInterval) {
            const interval = setInterval(fetchData, refreshInterval);
            return () => clearInterval(interval);
        }
    }, [url, refreshInterval]);
    
    return { data, loading, error };
};

// ==================== CHART COMPONENTS ====================

// Gauge Chart Component
const GaugeChart = ({ value, min = 0, max = 100, target, title, color = '#2563eb' }) => {
    const percentage = ((value - min) / (max - min)) * 100;
    const rotation = (percentage * 180) / 100 - 90;
    
    return (
        <div className="text-center">
            <h3 className="text-lg font-semibold mb-2">{title}</h3>
            <div className="relative inline-block">
                <svg width="200" height="120" className="transform -rotate-90">
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke="#e5e7eb"
                        strokeWidth="20"
                    />
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke={color}
                        strokeWidth="20"
                        strokeDasharray={`${percentage * 2.51} 251`}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="transform rotate-90">
                        <div className="text-3xl font-bold">{value}%</div>
                        <div className="text-sm text-gray-500">Hedef: {target}%</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Mini Sparkline Component
const Sparkline = ({ data, width = 100, height = 30, color = '#2563eb' }) => {
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;
    
    const points = data.map((value, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((value - min) / range) * height;
        return `${x},${y}`;
    }).join(' ');
    
    return (
        <svg width={width} height={height}>
            <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth="2"
            />
        </svg>
    );
};

// ==================== UTILITY FUNCTIONS ====================

const formatNumber = (num, decimals = 1) => {
    return Number(num).toFixed(decimals);
};

const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR');
};

const getStatusColor = (value, thresholds) => {
    if (value >= thresholds.good) return 'text-green-600';
    if (value >= thresholds.warning) return 'text-yellow-600';
    return 'text-red-600';
};

// Data aggregation functions
const calculateMovingAverage = (data, window = 3) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - window + 1);
        const subset = data.slice(start, i + 1);
        const avg = subset.reduce((a, b) => a + b, 0) / subset.length;
        result.push(avg);
    }
    return result;
};

const calculateControlLimits = (data) => {
    const mean = data.reduce((a, b) => a + b, 0) / data.length;
    const variance = data.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / data.length;
    const stdDev = Math.sqrt(variance);
    
    return {
        UCL: mean + 3 * stdDev,
        CL: mean,
        LCL: mean - 3 * stdDev,
        sigma: stdDev
    };
};

// ==================== ADVANCED COMPONENTS ====================

// Process Capability Box
const ProcessCapabilityBox = ({ cp, cpk, sigma, ppm }) => {
    const getCapabilityColor = (cpk) => {
        if (cpk >= 1.33) return 'bg-green-100 text-green-800';
        if (cpk >= 1.00) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    };
    
    return (
        <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">Süreç Yeterlilik</h3>
            <div className="grid grid-cols-2 gap-3">
                <div className="text-center">
                    <p className="text-xs text-gray-500">Cp</p>
                    <p className="text-xl font-bold">{cp}</p>
                </div>
                <div className="text-center">
                    <p className="text-xs text-gray-500">Cpk</p>
                    <p className={`text-xl font-bold rounded ${getCapabilityColor(cpk)} px-2 py-1`}>
                        {cpk}
                    </p>
                </div>
                <div className="text-center">
                    <p className="text-xs text-gray-500">Sigma</p>
                    <p className="text-xl font-bold">{sigma}σ</p>
                </div>
                <div className="text-center">
                    <p className="text-xs text-gray-500">PPM</p>
                    <p className="text-xl font-bold">{ppm.toLocaleString()}</p>
                </div>
            </div>
        </div>
    );
};

// Shift Performance Card
const ShiftPerformanceCard = ({ shift, metrics }) => {
    return (
        <div className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-center mb-3">
                <h4 className="font-semibold">{shift}</h4>
                <span className={`px-2 py-1 rounded text-xs ${
                    metrics.status === 'good' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                    {metrics.status === 'good' ? 'İyi' : 'Dikkat'}
                </span>
            </div>
            <div className="space-y-2">
                <div className="flex justify-between">
                    <span className="text-gray-500 text-sm">Verimlilik</span>
                    <span className="font-medium">{metrics.efficiency}%</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500 text-sm">Üretim</span>
                    <span className="font-medium">{metrics.production}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-500 text-sm">Hata</span>
                    <span className="font-medium">{metrics.defects}</span>
                </div>
            </div>
        </div>
    );
};

// Export all components
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        LoadingSpinner,
        ErrorBoundary,
        GaugeChart,
        Sparkline,
        ProcessCapabilityBox,
        ShiftPerformanceCard,
        useDataFetch,
        formatNumber,
        formatDate,
        getStatusColor,
        calculateMovingAverage,
        calculateControlLimits
    };
}