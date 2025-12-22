"""
Kontrol Grafikleri Modülü
Shewhart X̄-R, EWMA, CUSUM grafikleri ve Western Electric kuralları
"""

import numpy as np
import pandas as pd
import sys
import os

# Path ayarlaması
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader
from src.utils.statistics import StatisticalCalculator
from src.utils.constants import CONTROL_CONSTANTS

class ControlCharts:
    """
    İstatistiksel Proses Kontrol grafikleri sınıfı
    """
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Veri dosyası yolu
        """
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        self.stat_calc = StatisticalCalculator()
        
    def create_xbar_r_chart(self, variable='Aktif_Calisma_Saat', subgroup_size=1):
        """
        Shewhart X̄-R kontrol grafikleri oluşturur
        
        Args:
            variable: Analiz edilecek değişken
            subgroup_size: Alt grup büyüklüğü (n)
            
        Returns:
            dict: X̄ ve R grafikleri için veriler ve limitler
        """
        data = self.df[variable].values
        n = subgroup_size
        
        # Kontrol sabitleri
        constants = CONTROL_CONSTANTS.get(n, CONTROL_CONSTANTS[1])
        
        if n == 1:
            # Bireysel gözlemler için (I-MR grafiği)
            x_values = data
            mr_values = np.abs(np.diff(data))  # Moving Range
            
            # X̄ grafiği için
            x_bar = np.mean(x_values)
            mr_bar = np.mean(mr_values)
            sigma_estimate = mr_bar / constants['d2']
            
            # X grafiği limitleri
            x_ucl = x_bar + 3 * sigma_estimate
            x_cl = x_bar
            x_lcl = x_bar - 3 * sigma_estimate
            
            # MR grafiği limitleri
            mr_ucl = constants['D4'] * mr_bar
            mr_cl = mr_bar
            mr_lcl = constants['D3'] * mr_bar  # D3=0 for n≤6
            
            # Kontrol dışı noktaları tespit et
            x_out_of_control = []
            for i, val in enumerate(x_values):
                if val > x_ucl or val < x_lcl:
                    x_out_of_control.append({
                        'index': i,
                        'motor_id': self.df.iloc[i]['Motor_ID'],
                        'value': round(val, 2),
                        'type': 'Üst limit aşımı' if val > x_ucl else 'Alt limit aşımı'
                    })
            
            mr_out_of_control = []
            for i, val in enumerate(mr_values):
                if val > mr_ucl:
                    mr_out_of_control.append({
                        'index': i,
                        'value': round(val, 2),
                        'type': 'Değişkenlik artışı'
                    })
            
            return {
                'x_chart': {
                    'values': x_values.tolist(),
                    'UCL': round(x_ucl, 2),
                    'CL': round(x_cl, 2),
                    'LCL': round(x_lcl, 2),
                    'out_of_control': x_out_of_control,
                    'sigma_estimate': round(sigma_estimate, 3)
                },
                'mr_chart': {
                    'values': mr_values.tolist(),
                    'UCL': round(mr_ucl, 2),
                    'CL': round(mr_cl, 2),
                    'LCL': round(mr_lcl, 2),
                    'out_of_control': mr_out_of_control
                },
                'summary': {
                    'process_mean': round(x_bar, 2),
                    'process_sigma': round(sigma_estimate, 3),
                    'process_capability': round(x_bar / (3 * sigma_estimate), 3),
                    'control_status': 'Kontrol Altında' if len(x_out_of_control) == 0 else 'Kontrol Dışı'
                }
            }
        
        else:
            # Alt gruplar için (n>1)
            # Bu projede kullanılmıyor ama implement edildi
            subgroups = []
            x_bar_values = []
            r_values = []
            
            for i in range(0, len(data), n):
                subgroup = data[i:i+n]
                if len(subgroup) == n:
                    subgroups.append(subgroup)
                    x_bar_values.append(np.mean(subgroup))
                    r_values.append(np.max(subgroup) - np.min(subgroup))
            
            x_double_bar = np.mean(x_bar_values)
            r_bar = np.mean(r_values)
            
            # Limitler
            x_ucl = x_double_bar + constants['A2'] * r_bar
            x_lcl = x_double_bar - constants['A2'] * r_bar
            
            r_ucl = constants['D4'] * r_bar
            r_lcl = constants['D3'] * r_bar
            
            return {
                'x_bar_chart': {
                    'values': x_bar_values,
                    'UCL': round(x_ucl, 2),
                    'CL': round(x_double_bar, 2),
                    'LCL': round(x_lcl, 2)
                },
                'r_chart': {
                    'values': r_values,
                    'UCL': round(r_ucl, 2),
                    'CL': round(r_bar, 2),
                    'LCL': round(r_lcl, 2)
                }
            }
    
    def create_ewma_chart(self, variable='Verimlilik', lambda_val=0.2, L=3):
        """
        EWMA (Exponentially Weighted Moving Average) grafiği oluşturur
        
        Args:
            variable: Analiz edilecek değişken
            lambda_val: Yumuşatma parametresi (0<λ≤1, tipik 0.2)
            L: Kontrol limiti genişliği (tipik 2.7-3)
            
        Returns:
            dict: EWMA değerleri ve kontrol limitleri
        """
        data = self.df[variable].values
        n = len(data)
        
        # İlk değer için hedef (süreç ortalaması)
        mu0 = np.mean(data)
        sigma = np.std(data, ddof=1)
        
        # EWMA değerlerini hesapla
        z = np.zeros(n)
        z[0] = mu0  # veya data[0]
        
        for i in range(1, n):
            z[i] = lambda_val * data[i] + (1 - lambda_val) * z[i-1]
        
        # Kontrol limitlerini hesapla (zamanla daralır)
        ucl = []
        lcl = []
        
        for i in range(n):
            # Varyans zamanla azalır
            var_z = (lambda_val / (2 - lambda_val)) * (1 - (1 - lambda_val)**(2*(i+1)))
            std_z = sigma * np.sqrt(var_z)
            
            ucl.append(mu0 + L * std_z)
            lcl.append(mu0 - L * std_z)
        
        # Kontrol dışı noktaları tespit et
        out_of_control = []
        for i in range(n):
            if z[i] > ucl[i] or z[i] < lcl[i]:
                out_of_control.append({
                    'index': i,
                    'motor_id': self.df.iloc[i]['Motor_ID'],
                    'ewma_value': round(z[i], 2),
                    'actual_value': round(data[i], 2),
                    'type': 'Üst limit' if z[i] > ucl[i] else 'Alt limit'
                })
        
        # Trend analizi
        trend = 'Stabil'
        if len(z) > 10:
            recent_trend = z[-10:]
            if all(recent_trend[i] > recent_trend[i-1] for i in range(1, len(recent_trend))):
                trend = 'Artan'
            elif all(recent_trend[i] < recent_trend[i-1] for i in range(1, len(recent_trend))):
                trend = 'Azalan'
        
        return {
            'ewma_values': z.tolist(),
            'UCL': [round(u, 2) for u in ucl],
            'CL': round(mu0, 2),
            'LCL': [round(l, 2) for l in lcl],
            'actual_values': data.tolist(),
            'out_of_control': out_of_control,
            'parameters': {
                'lambda': lambda_val,
                'L': L,
                'process_mean': round(mu0, 2),
                'process_sigma': round(sigma, 3)
            },
            'summary': {
                'control_status': 'Kontrol Altında' if len(out_of_control) == 0 else 'Kontrol Dışı',
                'trend': trend,
                'sensitivity': 'Küçük kaymalara duyarlı' if lambda_val < 0.3 else 'Normal'
            }
        }
    
    def create_cusum_chart(self, variable='Toplam_Uretim_Suresi', k=0.5, h=5):
        """
        CUSUM (Cumulative Sum) kontrol grafiği oluşturur
        
        Args:
            variable: Analiz edilecek değişken
            k: Referans değeri (slack value), tipik 0.5σ
            h: Karar aralığı (decision interval), tipik 4-5σ
            
        Returns:
            dict: CUSUM değerleri ve alarmlar
        """
        data = self.df[variable].values
        n = len(data)
        
        # Hedef değer ve standart sapma
        mu0 = np.mean(data)
        sigma = np.std(data, ddof=1)
        
        # Standardize et
        z = (data - mu0) / sigma
        
        # CUSUM değerlerini hesapla
        c_plus = np.zeros(n)   # Yukarı yönlü kaymalar için
        c_minus = np.zeros(n)  # Aşağı yönlü kaymalar için
        
        for i in range(1, n):
            c_plus[i] = max(0, z[i] - k + c_plus[i-1])
            c_minus[i] = max(0, -z[i] - k + c_minus[i-1])
        
        # Kontrol dışı noktaları ve alarm noktalarını tespit et
        alarms = []
        for i in range(n):
            if c_plus[i] > h:
                alarms.append({
                    'index': i,
                    'motor_id': self.df.iloc[i]['Motor_ID'],
                    'type': 'Yukarı kayma',
                    'cusum_value': round(c_plus[i], 2),
                    'actual_value': round(data[i], 2)
                })
            elif c_minus[i] > h:
                alarms.append({
                    'index': i,
                    'motor_id': self.df.iloc[i]['Motor_ID'],
                    'type': 'Aşağı kayma',
                    'cusum_value': round(c_minus[i], 2),
                    'actual_value': round(data[i], 2)
                })
        
        # Kayma tespiti
        shift_detected = None
        if any(c_plus > h):
            first_alarm_index = np.where(c_plus > h)[0][0]
            # Geriye doğru git ve kaymayı bul
            for j in range(first_alarm_index, -1, -1):
                if c_plus[j] == 0:
                    shift_detected = j + 1
                    break
        
        return {
            'C_plus': c_plus.tolist(),
            'C_minus': c_minus.tolist(),
            'h_limit': h,
            'k_reference': k,
            'alarms': alarms,
            'actual_values': data.tolist(),
            'standardized_values': z.tolist(),
            'summary': {
                'control_status': 'Kontrol Altında' if len(alarms) == 0 else 'Kontrol Dışı',
                'total_alarms': len(alarms),
                'shift_start_index': shift_detected,
                'parameters': {
                    'target': round(mu0, 2),
                    'sigma': round(sigma, 3),
                    'k_in_sigma': f"{k}σ",
                    'h_in_sigma': f"{h}σ"
                }
            }
        }
    
    def check_western_electric_rules(self, variable='Aktif_Calisma_Saat'):
        """
        Western Electric kurallarını kontrol eder
        
        Rules:
        1. 1 nokta 3σ dışında
        2. 3'ten 2 nokta aynı tarafta 2σ ötesinde
        3. 5'ten 4 nokta aynı tarafta 1σ ötesinde
        4. 8 ardışık nokta merkez çizgisinin aynı tarafında
        5. 6 ardışık nokta sürekli artan/azalan (trend)
        6. 14 ardışık nokta yukarı-aşağı dalgalanma (zigzag)
        
        Returns:
            dict: Her kural için ihlaller
        """
        data = self.df[variable].values
        mean = np.mean(data)
        sigma = np.std(data, ddof=1)
        
        violations = {
            'rule1': [],  # 3σ kuralı
            'rule2': [],  # 2σ kuralı
            'rule3': [],  # 1σ kuralı
            'rule4': [],  # Run kuralı
            'rule5': [],  # Trend kuralı
            'rule6': []   # Zigzag kuralı
        }
        
        # Rule 1: 1 nokta 3σ dışında
        for i in range(len(data)):
            if abs(data[i] - mean) > 3 * sigma:
                violations['rule1'].append({
                    'index': i,
                    'motor_id': self.df.iloc[i]['Motor_ID'],
                    'value': round(data[i], 2),
                    'sigma_distance': round((data[i] - mean) / sigma, 2)
                })
        
        # Rule 2: 3'ten 2 nokta 2σ ötesinde
        for i in range(len(data) - 2):
            subset = data[i:i+3]
            above = sum(1 for x in subset if x > mean + 2*sigma)
            below = sum(1 for x in subset if x < mean - 2*sigma)
            
            if above >= 2 or below >= 2:
                violations['rule2'].append({
                    'start_index': i,
                    'end_index': i+2,
                    'motor_ids': self.df.iloc[i:i+3]['Motor_ID'].tolist(),
                    'direction': 'Üst' if above >= 2 else 'Alt'
                })
        
        # Rule 3: 5'ten 4 nokta 1σ ötesinde
        for i in range(len(data) - 4):
            subset = data[i:i+5]
            above = sum(1 for x in subset if x > mean + sigma)
            below = sum(1 for x in subset if x < mean - sigma)
            
            if above >= 4 or below >= 4:
                violations['rule3'].append({
                    'start_index': i,
                    'end_index': i+4,
                    'direction': 'Üst' if above >= 4 else 'Alt'
                })
        
        # Rule 4: 8 ardışık nokta aynı tarafta
        for i in range(len(data) - 7):
            subset = data[i:i+8]
            if all(x > mean for x in subset) or all(x < mean for x in subset):
                violations['rule4'].append({
                    'start_index': i,
                    'end_index': i+7,
                    'motor_ids': self.df.iloc[i:i+8]['Motor_ID'].tolist(),
                    'side': 'Üst' if subset[0] > mean else 'Alt'
                })
        
        # Rule 5: 6 ardışık artan/azalan
        for i in range(len(data) - 5):
            subset = data[i:i+6]
            increasing = all(subset[j] > subset[j-1] for j in range(1, 6))
            decreasing = all(subset[j] < subset[j-1] for j in range(1, 6))
            
            if increasing or decreasing:
                violations['rule5'].append({
                    'start_index': i,
                    'end_index': i+5,
                    'trend': 'Artan' if increasing else 'Azalan'
                })
        
        # Rule 6: 14 ardışık zigzag
        for i in range(len(data) - 13):
            subset = data[i:i+14]
            zigzag = True
            for j in range(2, 14):
                if not ((subset[j] > subset[j-1] and subset[j-1] < subset[j-2]) or
                       (subset[j] < subset[j-1] and subset[j-1] > subset[j-2])):
                    zigzag = False
                    break
            
            if zigzag:
                violations['rule6'].append({
                    'start_index': i,
                    'end_index': i+13,
                    'pattern': 'Zigzag'
                })
        
        # Özet
        total_violations = sum(len(v) for v in violations.values())
        
        return {
            'violations': violations,
            'summary': {
                'total_violations': total_violations,
                'violated_rules': [rule for rule, v in violations.items() if len(v) > 0],
                'control_status': 'Kontrol Altında' if total_violations == 0 else 'Kontrol Dışı',
                'most_common_violation': max(violations.items(), key=lambda x: len(x[1]))[0] if total_violations > 0 else None
            }
        }
    
    def generate_control_chart_report(self):
        """
        Tüm kontrol grafikleri için özet rapor
        """
        # X̄-MR grafiği
        xbar_r = self.create_xbar_r_chart('Toplam_Uretim_Suresi')
        
        # EWMA grafiği
        ewma = self.create_ewma_chart('Verimlilik')
        
        # CUSUM grafiği
        cusum = self.create_cusum_chart('Toplam_Uretim_Suresi')
        
        # Western Electric kuralları
        we_rules = self.check_western_electric_rules('Aktif_Calisma_Saat')
        
        return {
            'xbar_mr': {
                'status': xbar_r['summary']['control_status'],
                'out_of_control_count': len(xbar_r['x_chart']['out_of_control']),
                'process_mean': xbar_r['summary']['process_mean'],
                'process_sigma': xbar_r['summary']['process_sigma']
            },
            'ewma': {
                'status': ewma['summary']['control_status'],
                'trend': ewma['summary']['trend'],
                'out_of_control_count': len(ewma['out_of_control'])
            },
            'cusum': {
                'status': cusum['summary']['control_status'],
                'alarms': len(cusum['alarms'])
            },
            'western_electric': {
                'status': we_rules['summary']['control_status'],
                'total_violations': we_rules['summary']['total_violations'],
                'violated_rules': we_rules['summary']['violated_rules']
            },
            'overall_status': self._determine_overall_status(
                xbar_r['summary']['control_status'],
                ewma['summary']['control_status'],
                cusum['summary']['control_status'],
                we_rules['summary']['control_status']
            )
        }
    
    def _determine_overall_status(self, *statuses):
        """
        Genel kontrol durumunu belirler
        """
        if all(s == 'Kontrol Altında' for s in statuses):
            return 'Süreç Kontrol Altında'
        elif sum(s == 'Kontrol Dışı' for s in statuses) >= 2:
            return 'Süreç Kontrol Dışı - Acil Müdahale Gerekli'
        else:
            return 'Süreç İzlenmeli - Potansiyel Problem'


# TEST KODU
if __name__ == "__main__":
    print("=== KONTROL GRAFİKLERİ ANALİZİ ===\n")
    
    charts = ControlCharts()
    
    # 1. X̄-MR Grafiği
    print("1. Shewhart X̄-MR Grafiği (Toplam Üretim Süresi):")
    xbar_r = charts.create_xbar_r_chart('Toplam_Uretim_Suresi')
    print(f"   Süreç Ortalaması: {xbar_r['summary']['process_mean']} saat")
    print(f"   Üst Kontrol Limiti: {xbar_r['x_chart']['UCL']} saat")
    print(f"   Alt Kontrol Limiti: {xbar_r['x_chart']['LCL']} saat")
    print(f"   Kontrol Dışı Nokta: {len(xbar_r['x_chart']['out_of_control'])} adet")
    print(f"   Durum: {xbar_r['summary']['control_status']}")
    
    # 2. EWMA Grafiği
    print("\n2. EWMA Grafiği (Verimlilik):")
    ewma = charts.create_ewma_chart('Verimlilik', lambda_val=0.2)
    print(f"   Trend: {ewma['summary']['trend']}")
    print(f"   Kontrol Dışı: {len(ewma['out_of_control'])} nokta")
    print(f"   Durum: {ewma['summary']['control_status']}")
    
    # 3. Western Electric Kuralları
    print("\n3. Western Electric Kuralları (Aktif Çalışma):")
    we_rules = charts.check_western_electric_rules('Aktif_Calisma_Saat')
    print(f"   Toplam İhlal: {we_rules['summary']['total_violations']}")
    print(f"   İhlal Edilen Kurallar: {we_rules['summary']['violated_rules']}")
    
    # 4. Genel Özet
    print("\n4. GENEL DURUM:")
    report = charts.generate_control_chart_report()
    print(f"   {report['overall_status']}")