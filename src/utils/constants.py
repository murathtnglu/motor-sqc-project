"""
Sabitler ve parametreler
"""

# Kontrol limitleri sabitleri
CONTROL_CONSTANTS = {
    1: {'A2': 2.659, 'D3': 0, 'D4': 3.267, 'd2': 1.128},
    2: {'A2': 1.880, 'D3': 0, 'D4': 3.267, 'd2': 1.128},
    3: {'A2': 1.023, 'D3': 0, 'D4': 2.574, 'd2': 1.693},
    4: {'A2': 0.729, 'D3': 0, 'D4': 2.282, 'd2': 2.059},
    5: {'A2': 0.577, 'D3': 0, 'D4': 2.114, 'd2': 2.326}
}

# Spesifikasyon limitleri
SPEC_LIMITS = {
    'Toplam_Uretim_Suresi': {
        'USL': 70,  # Upper Specification Limit
        'LSL': 55,  # Lower Specification Limit
        'Target': 60
    },
    'Aktif_Calisma_Saat': {
        'USL': 60,
        'LSL': 50,
        'Target': 55
    }
}

# Hedef değerler
TARGETS = {
    'OEE': 85,  # %
    'Verimlilik': 90,  # %
    'Kalite': 99,  # %
    'Hata_Orani': 2  # %
}

# Renk şemaları
COLORS = {
    'primary': '#2563eb',
    'success': '#10b981',
    'warning': '#f59e0b', 
    'danger': '#ef4444',
    'info': '#3b82f6'
}