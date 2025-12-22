"""
İstatistik fonksiyonları modülü
Kontrol limitleri, yeterlilik indeksleri, sigma hesaplamaları
"""

import numpy as np
import pandas as pd
from scipy import stats
from .constants import CONTROL_CONSTANTS, SPEC_LIMITS

class StatisticalCalculator:
    """İstatistiksel hesaplamalar için ana sınıf"""
    
    @staticmethod
    def calculate_control_limits(data, chart_type='xbar', subgroup_size=1):
        """
        Kontrol grafikleri için limit hesaplaması
        
        Args:
            data: Veri array'i
            chart_type: 'xbar', 'r', 'mr' (moving range)
            subgroup_size: Alt grup büyüklüğü (n)
            
        Returns:
            dict: UCL, CL, LCL değerleri
        """
        n = subgroup_size
        constants = CONTROL_CONSTANTS.get(n, CONTROL_CONSTANTS[1])
        
        if chart_type == 'xbar':
            # X-bar grafiği için
            x_bar = np.mean(data)
            
            # Moving Range hesapla (n=1 için)
            if n == 1:
                mr = np.abs(np.diff(data))
                mr_bar = np.mean(mr)
                sigma_estimate = mr_bar / constants['d2']
            else:
                # Alt gruplar için range hesapla
                ranges = []
                for i in range(0, len(data), n):
                    subgroup = data[i:i+n]
                    if len(subgroup) == n:
                        ranges.append(np.max(subgroup) - np.min(subgroup))
                r_bar = np.mean(ranges)
                sigma_estimate = r_bar / constants['d2']
            
            # 3-sigma limitleri
            ucl = x_bar + 3 * sigma_estimate
            cl = x_bar
            lcl = x_bar - 3 * sigma_estimate
            
            return {
                'UCL': round(ucl, 2),
                'CL': round(cl, 2),
                'LCL': round(lcl, 2),
                'sigma': round(sigma_estimate, 3)
            }
            
        elif chart_type == 'mr':
            # Moving Range grafiği için
            mr = np.abs(np.diff(data))
            mr_bar = np.mean(mr)
            
            ucl = constants['D4'] * mr_bar
            cl = mr_bar
            lcl = constants['D3'] * mr_bar  # n<=6 için D3=0
            
            return {
                'UCL': round(ucl, 2),
                'CL': round(cl, 2),
                'LCL': round(lcl, 2)
            }
            
        elif chart_type == 'r':
            # R (Range) grafiği için
            ranges = []
            for i in range(0, len(data), n):
                subgroup = data[i:i+n]
                if len(subgroup) == n:
                    ranges.append(np.max(subgroup) - np.min(subgroup))
            
            r_bar = np.mean(ranges)
            
            ucl = constants['D4'] * r_bar
            cl = r_bar
            lcl = constants['D3'] * r_bar
            
            return {
                'UCL': round(ucl, 2),
                'CL': round(cl, 2),
                'LCL': round(lcl, 2)
            }
    
    @staticmethod
    def calculate_process_capability(data, spec_limits=None):
        """
        Süreç yeterlilik indekslerini hesaplar (Cp, Cpk, Cpm)
        
        Args:
            data: Veri array'i
            spec_limits: {'USL': üst_limit, 'LSL': alt_limit, 'Target': hedef}
            
        Returns:
            dict: Cp, Cpk, Cpm değerleri ve yorumları
        """
        if spec_limits is None:
            return None
            
        mean = np.mean(data)
        std = np.std(data, ddof=1)  # Sample standard deviation
        
        usl = spec_limits.get('USL')
        lsl = spec_limits.get('LSL')
        target = spec_limits.get('Target', (usl + lsl) / 2)
        
        # Cp: Potansiyel yeterlilik (merkezlenme göz ardı)
        cp = (usl - lsl) / (6 * std)
        
        # Cpk: Gerçek yeterlilik (merkezlenme dahil)
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)
        
        # Cpm: Taguchi yeterlilik (hedeften sapma cezalı)
        msd = std**2 + (mean - target)**2  # Mean Square Deviation
        cpm = (usl - lsl) / (6 * np.sqrt(msd))
        
        # Yeterlilik yorumu
        def interpret_capability(cpk_value):
            if cpk_value < 0.67:
                return "Yetersiz (Acil müdahale gerekli)"
            elif cpk_value < 1.00:
                return "Zayıf (İyileştirme gerekli)"
            elif cpk_value < 1.33:
                return "Kabul edilebilir (3-sigma)"
            elif cpk_value < 1.67:
                return "İyi (4-sigma)"
            else:
                return "Mükemmel (5-sigma+)"
        
        # PPM (Parts Per Million) hata tahmini
        z_usl = (usl - mean) / std
        z_lsl = (lsl - mean) / std
        ppm_usl = (1 - stats.norm.cdf(z_usl)) * 1_000_000
        ppm_lsl = stats.norm.cdf(z_lsl) * 1_000_000
        ppm_total = ppm_usl + ppm_lsl
        
        return {
            'Cp': round(cp, 3),
            'Cpk': round(cpk, 3),
            'Cpm': round(cpm, 3),
            'CPU': round(cpu, 3),
            'CPL': round(cpl, 3),
            'mean': round(mean, 2),
            'std': round(std, 3),
            'interpretation': interpret_capability(cpk),
            'sigma_level': round(3 + cpk, 1),
            'PPM': round(ppm_total, 0)
        }
    
    @staticmethod
    def calculate_ewma(data, lambda_val=0.2, L=3):
        """
        EWMA (Exponentially Weighted Moving Average) hesaplaması
        
        Args:
            data: Veri array'i
            lambda_val: Yumuşatma parametresi (0-1 arası, tipik 0.2)
            L: Kontrol limiti genişliği (tipik 3)
            
        Returns:
            dict: EWMA değerleri ve kontrol limitleri
        """
        z = np.zeros(len(data))
        z[0] = np.mean(data)  # İlk değer ortalama
        
        # EWMA hesapla
        for i in range(1, len(data)):
            z[i] = lambda_val * data[i] + (1 - lambda_val) * z[i-1]
        
        # Kontrol limitleri
        mu = np.mean(data)
        sigma = np.std(data, ddof=1)
        
        # UCL ve LCL zamanla daralır
        ucl = []
        lcl = []
        for i in range(len(data)):
            factor = np.sqrt(lambda_val / (2 - lambda_val) * 
                           (1 - (1 - lambda_val)**(2*(i+1))))
            ucl.append(mu + L * sigma * factor)
            lcl.append(mu - L * sigma * factor)
        
        return {
            'ewma_values': z.tolist(),
            'UCL': ucl,
            'LCL': lcl,
            'center_line': mu
        }
    
    @staticmethod
    def calculate_cusum(data, k=0.5, h=5):
        """
        CUSUM (Cumulative Sum) kontrol grafiği hesaplaması
        
        Args:
            data: Veri array'i
            k: Referans değeri (tipik 0.5σ)
            h: Karar aralığı (tipik 4 veya 5)
            
        Returns:
            dict: CUSUM değerleri ve kontrol dışı noktalar
        """
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        # Standardize et
        z = (data - mean) / std
        
        # CUSUM hesapla
        c_plus = np.zeros(len(data))
        c_minus = np.zeros(len(data))
        
        for i in range(1, len(data)):
            c_plus[i] = max(0, z[i] - k + c_plus[i-1])
            c_minus[i] = max(0, -z[i] - k + c_minus[i-1])
        
        # Kontrol dışı noktaları tespit et
        out_of_control = []
        for i in range(len(data)):
            if c_plus[i] > h or c_minus[i] > h:
                out_of_control.append(i)
        
        return {
            'C_plus': c_plus.tolist(),
            'C_minus': c_minus.tolist(),
            'h_limit': h,
            'out_of_control_points': out_of_control
        }
    
    @staticmethod
    def check_western_electric_rules(data, control_limits):
        """
        Western Electric kurallarını kontrol eder
        
        Rules:
        1. 1 nokta 3σ dışında
        2. 3'ten 2 nokta aynı tarafta 2σ ötesinde
        3. 5'ten 4 nokta aynı tarafta 1σ ötesinde
        4. 8 ardışık nokta merkez çizgisinin aynı tarafında
        
        Args:
            data: Veri array'i
            control_limits: {'UCL', 'CL', 'LCL', 'sigma'} değerleri
            
        Returns:
            dict: Her kural için ihlal eden noktalar
        """
        cl = control_limits['CL']
        sigma = control_limits['sigma']
        
        violations = {
            'rule1': [],  # 3σ dışında
            'rule2': [],  # 2σ kuralı
            'rule3': [],  # 1σ kuralı
            'rule4': []   # Run kuralı
        }
        
        # Rule 1: 3σ dışında
        for i, val in enumerate(data):
            if val > cl + 3*sigma or val < cl - 3*sigma:
                violations['rule1'].append(i)
        
        # Rule 2: 3'ten 2 nokta 2σ ötesinde
        for i in range(len(data) - 2):
            subset = data[i:i+3]
            above_2sigma = sum(s > cl + 2*sigma for s in subset)
            below_2sigma = sum(s < cl - 2*sigma for s in subset)
            if above_2sigma >= 2 or below_2sigma >= 2:
                violations['rule2'].extend(range(i, i+3))
        
        # Rule 3: 5'ten 4 nokta 1σ ötesinde
        for i in range(len(data) - 4):
            subset = data[i:i+5]
            above_1sigma = sum(s > cl + sigma for s in subset)
            below_1sigma = sum(s < cl - sigma for s in subset)
            if above_1sigma >= 4 or below_1sigma >= 4:
                violations['rule3'].extend(range(i, i+5))
        
        # Rule 4: 8 ardışık nokta aynı tarafta
        for i in range(len(data) - 7):
            subset = data[i:i+8]
            if all(s > cl for s in subset) or all(s < cl for s in subset):
                violations['rule4'].extend(range(i, i+8))
        
        # Tekrarları temizle
        for rule in violations:
            violations[rule] = list(set(violations[rule]))
        
        return violations
    
    @staticmethod
    def calculate_oee_components(data_df):
        """
        OEE (Overall Equipment Effectiveness) bileşenlerini hesaplar
        
        Args:
            data_df: Motor verileri DataFrame'i
            
        Returns:
            dict: Availability, Performance, Quality ve OEE
        """
        # Availability (Kullanılabilirlik)
        total_time = data_df['Toplam_Uretim_Suresi'].sum()
        downtime = data_df['Durma_Suresi_Saat'].sum()
        availability = ((total_time - downtime) / total_time) * 100
        
        # Performance (Performans)
        # Ideal çevrim süresi olmadığı için %100 varsayıyoruz
        # Gerçek uygulamada: (İdeal Çevrim × Üretilen) / Çalışma Süresi
        performance = 100.0
        
        # Quality (Kalite)
        total_produced = len(data_df)
        good_products = len(data_df[data_df['Hata_Nedeni'] == '-'])
        quality = (good_products / total_produced) * 100
        
        # OEE
        oee = (availability * performance * quality) / 10000
        
        return {
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'oee': round(oee, 2)
        }


# TEST KODU
if __name__ == "__main__":
    # Test verileri oluştur
    np.random.seed(42)
    test_data = np.random.normal(55, 3, 100)  # Ortalama 55, std 3
    
    # Kontrol limitleri
    print("=== KONTROL LİMİTLERİ ===")
    calc = StatisticalCalculator()
    limits = calc.calculate_control_limits(test_data)
    print(f"X-bar Kontrol Limitleri: {limits}")
    
    # Süreç yeterlilik
    print("\n=== SÜREÇ YETERLİLİK ===")
    spec = {'USL': 70, 'LSL': 55, 'Target': 60}
    capability = calc.calculate_process_capability(test_data, spec)
    print(f"Cp: {capability['Cp']}, Cpk: {capability['Cpk']}")
    print(f"Yorum: {capability['interpretation']}")
    
    # EWMA
    print("\n=== EWMA ===")
    ewma_result = calc.calculate_ewma(test_data[:20])
    print(f"İlk 5 EWMA değeri: {ewma_result['ewma_values'][:5]}")