"""
Süreç Yeterlilik Analizi Modülü
Cp, Cpk, Cpm indeksleri ve sigma seviyesi hesaplamaları
"""

import numpy as np
import pandas as pd
from scipy import stats
import sys
import os

# Path ayarlaması
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader
from src.utils.statistics import StatisticalCalculator
from src.utils.constants import SPEC_LIMITS

class ProcessCapability:
    """
    Süreç yeterlilik analizi sınıfı
    """
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Veri dosyası yolu
        """
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        self.stat_calc = StatisticalCalculator()
        
    def calculate_capability_indices(self, variable='Toplam_Uretim_Suresi', 
                                    usl=None, lsl=None, target=None):
        """
        Cp, Cpk, Cpm, Pp, Ppk indekslerini hesaplar
        
        Args:
            variable: Analiz edilecek değişken
            usl: Üst spesifikasyon limiti
            lsl: Alt spesifikasyon limiti
            target: Hedef değer
            
        Returns:
            dict: Yeterlilik indeksleri ve yorumları
        """
        # Veriyi al
        data = self.df[variable].values
        
        # Spesifikasyon limitlerini belirle
        if usl is None or lsl is None:
            if variable in SPEC_LIMITS:
                spec = SPEC_LIMITS[variable]
                usl = spec['USL']
                lsl = spec['LSL']
                target = spec.get('Target', (usl + lsl) / 2)
            else:
                # Varsayılan: ortalama ± 3 sigma
                mean = np.mean(data)
                std = np.std(data, ddof=1)
                usl = mean + 3 * std
                lsl = mean - 3 * std
                target = mean
        
        if target is None:
            target = (usl + lsl) / 2
        
        # Temel istatistikler
        mean = np.mean(data)
        std_within = np.std(data, ddof=1)  # Kısa dönem varyasyon (within)
        
        # Moving Range ile sigma tahmini (within variation)
        mr = np.abs(np.diff(data))
        mr_bar = np.mean(mr)
        sigma_within = mr_bar / 1.128  # d2 for n=2
        
        # Overall variation
        sigma_overall = np.std(data, ddof=1)
        
        # 1. Cp - Potansiyel Yeterlilik (merkezlenme yok sayılır)
        cp = (usl - lsl) / (6 * sigma_within)
        
        # 2. Cpk - Gerçek Yeterlilik (merkezlenme dahil)
        cpu = (usl - mean) / (3 * sigma_within)
        cpl = (mean - lsl) / (3 * sigma_within)
        cpk = min(cpu, cpl)
        
        # 3. Cpm - Taguchi Yeterlilik (hedeften sapma cezalı)
        msd = sigma_within**2 + (mean - target)**2
        cpm = (usl - lsl) / (6 * np.sqrt(msd))
        
        # 4. Pp - Potansiyel Performans (overall variation)
        pp = (usl - lsl) / (6 * sigma_overall)
        
        # 5. Ppk - Gerçek Performans
        ppu = (usl - mean) / (3 * sigma_overall)
        ppl = (mean - lsl) / (3 * sigma_overall)
        ppk = min(ppu, ppl)
        
        # 6. Merkezlenme İndeksi (Cp ile Cpk farkı)
        k = abs(mean - target) / ((usl - lsl) / 2)
        
        # 7. Sigma Seviyesi
        # Z-bench hesaplama
        z_bench = 3 * cpk
        sigma_level = z_bench + 1.5  # 1.5 sigma kayma dahil
        
        # 8. PPM (Parts Per Million) Hesaplamaları
        # Normal dağılım varsayımı ile
        z_usl = (usl - mean) / sigma_within
        z_lsl = (lsl - mean) / sigma_within
        
        # Spec dışı oranlar
        p_above_usl = 1 - stats.norm.cdf(z_usl)
        p_below_lsl = stats.norm.cdf(z_lsl)
        p_total_defect = p_above_usl + p_below_lsl
        
        # PPM'e çevir
        ppm_above = p_above_usl * 1_000_000
        ppm_below = p_below_lsl * 1_000_000
        ppm_total = ppm_above + ppm_below
        
        # 9. Gerçek Hata Oranı (Observed)
        actual_above = sum(data > usl)
        actual_below = sum(data < lsl)
        actual_total = actual_above + actual_below
        actual_ppm = (actual_total / len(data)) * 1_000_000
        
        # 10. Yeterlilik Yorumlama
        def interpret_capability(cpk_val):
            if cpk_val < 0:
                return "Süreç spec dışında üretiyor - Acil müdahale!"
            elif cpk_val < 0.67:
                return "Yetersiz - Süreç iyileştirmesi kritik"
            elif cpk_val < 1.00:
                return "Zayıf - 3-sigma altı, iyileştirme gerekli"
            elif cpk_val < 1.33:
                return "Kabul edilebilir - 3-sigma seviyesi"
            elif cpk_val < 1.67:
                return "İyi - 4-sigma seviyesi"
            elif cpk_val < 2.00:
                return "Mükemmel - 5-sigma seviyesi"
            else:
                return "Dünya sınıfı - 6-sigma seviyesi"
        
        return {
            'indices': {
                'Cp': round(cp, 3),
                'Cpk': round(cpk, 3),
                'CPU': round(cpu, 3),
                'CPL': round(cpl, 3),
                'Cpm': round(cpm, 3),
                'Pp': round(pp, 3),
                'Ppk': round(ppk, 3),
                'k': round(k, 3)
            },
            'statistics': {
                'mean': round(mean, 2),
                'target': round(target, 2),
                'sigma_within': round(sigma_within, 3),
                'sigma_overall': round(sigma_overall, 3),
                'USL': usl,
                'LSL': lsl
            },
            'sigma_level': round(sigma_level, 2),
            'ppm': {
                'expected_above_USL': round(ppm_above, 0),
                'expected_below_LSL': round(ppm_below, 0),
                'expected_total': round(ppm_total, 0),
                'observed_total': round(actual_ppm, 0)
            },
            'interpretation': {
                'capability_status': interpret_capability(cpk),
                'centering': 'İyi merkezlenmiş' if k < 0.2 else 'Kayma var',
                'variation_control': 'İyi' if cp > 1.33 else 'Yüksek varyasyon',
                'recommendation': self._get_recommendation(cp, cpk, k)
            }
        }
    
    def _get_recommendation(self, cp, cpk, k):
        """
        Cp, Cpk ve k değerlerine göre öneri üretir
        """
        if cpk < 0.67:
            return "Acil: Süreç ortalamasını hedefe kaydırın ve varyasyonu azaltın"
        elif cp > 1.33 and cpk < 1.00:
            return "Süreç potansiyeli yeterli, sadece merkezleme gerekli"
        elif cp < 1.00:
            return "Varyasyon çok yüksek, süreç iyileştirme gerekli"
        elif cpk >= 1.33:
            return "Süreç yeterli, mevcut performansı koruyun"
        else:
            return "Hem merkezleme hem varyasyon iyileştirmesi yapın"
    
    def calculate_for_all_variables(self):
        """
        Tüm kritik değişkenler için yeterlilik analizi
        """
        variables = {
            'Toplam_Uretim_Suresi': SPEC_LIMITS.get('Toplam_Uretim_Suresi'),
            'Aktif_Calisma_Saat': SPEC_LIMITS.get('Aktif_Calisma_Saat'),
            'Verimlilik': {'USL': 100, 'LSL': 85, 'Target': 95}
        }
        
        results = {}
        for var, spec in variables.items():
            if var in self.df.columns:
                if spec:
                    cap = self.calculate_capability_indices(
                        var, 
                        spec['USL'], 
                        spec['LSL'], 
                        spec.get('Target')
                    )
                    results[var] = {
                        'Cpk': cap['indices']['Cpk'],
                        'Sigma': cap['sigma_level'],
                        'PPM': cap['ppm']['expected_total'],
                        'Status': cap['interpretation']['capability_status']
                    }
        
        return results
    
    def analyze_by_shift(self, variable='Toplam_Uretim_Suresi'):
        """
        Vardiya bazlı yeterlilik analizi
        """
        shifts = self.df['Vardiya'].unique()
        shift_results = {}
        
        for shift in shifts:
            shift_data = self.df[self.df['Vardiya'] == shift]
            data = shift_data[variable].values
            
            if variable in SPEC_LIMITS:
                spec = SPEC_LIMITS[variable]
                mean = np.mean(data)
                std = np.std(data, ddof=1)
                
                # Cpk hesapla
                cpu = (spec['USL'] - mean) / (3 * std)
                cpl = (mean - spec['LSL']) / (3 * std)
                cpk = min(cpu, cpl)
                
                shift_results[shift] = {
                    'sample_size': len(data),
                    'mean': round(mean, 2),
                    'std': round(std, 3),
                    'cpk': round(cpk, 3),
                    'performance': 'İyi' if cpk >= 1.33 else 'İyileştirme Gerekli'
                }
        
        return shift_results
    
    def capability_improvement_analysis(self, variable='Toplam_Uretim_Suresi'):
        """
        Yeterlilik iyileştirme analizi
        Ne kadar iyileştirme gerekli?
        """
        current = self.calculate_capability_indices(variable)
        
        # Hedef Cpk = 1.33 için gerekli iyileştirme
        current_cpk = current['indices']['Cpk']
        current_sigma = current['statistics']['sigma_within']
        current_mean = current['statistics']['mean']
        target = current['statistics']['target']
        
        # Gerekli sigma azaltımı
        if current_cpk < 1.33:
            required_sigma = abs(current_mean - target) / (1.33 * 3)
            sigma_reduction_needed = ((current_sigma - required_sigma) / current_sigma) * 100
        else:
            sigma_reduction_needed = 0
        
        # Merkezleme iyileştirmesi
        centering_improvement = abs(current_mean - target)
        
        return {
            'current_state': {
                'cpk': current_cpk,
                'sigma': round(current_sigma, 3),
                'mean_offset': round(current_mean - target, 2)
            },
            'improvement_needed': {
                'for_cpk_1.33': {
                    'sigma_reduction_%': round(max(0, sigma_reduction_needed), 1),
                    'centering_adjustment': round(centering_improvement, 2)
                },
                'for_cpk_1.67': {
                    'sigma_reduction_%': round(max(0, ((current_sigma - abs(current_mean - target)/(1.67*3)) / current_sigma) * 100), 1)
                }
            },
            'expected_benefits': {
                'defect_reduction_%': round((1 - stats.norm.cdf(-3*1.33)*2 / (1 - stats.norm.cdf(-3*current_cpk)*2)) * 100, 1) if current_cpk > 0 else 0,
                'ppm_improvement': round(current['ppm']['expected_total'] - 63, 0)  # 63 PPM for Cpk=1.33
            }
        }
    
    def generate_capability_report(self):
        """
        Kapsamlı yeterlilik raporu
        """
        # Ana değişken analizi
        main_cap = self.calculate_capability_indices('Toplam_Uretim_Suresi')
        
        # Tüm değişkenler
        all_vars = self.calculate_for_all_variables()
        
        # Vardiya analizi
        shift_analysis = self.analyze_by_shift()
        
        # İyileştirme analizi
        improvement = self.capability_improvement_analysis()
        
        # Özet rapor
        report = {
            'executive_summary': {
                'overall_cpk': main_cap['indices']['Cpk'],
                'sigma_level': main_cap['sigma_level'],
                'expected_ppm': main_cap['ppm']['expected_total'],
                'capability_status': main_cap['interpretation']['capability_status']
            },
            'all_variables': all_vars,
            'shift_performance': shift_analysis,
            'improvement_roadmap': improvement,
            'key_findings': [],
            'recommendations': []
        }
        
        # Bulgular
        if main_cap['indices']['Cpk'] < 1.00:
            report['key_findings'].append("Süreç yeterliliği 3-sigma seviyesinin altında")
        
        if main_cap['indices']['Cp'] > main_cap['indices']['Cpk'] * 1.5:
            report['key_findings'].append("Süreç merkezlenmesi kötü, potansiyel yüksek")
        
        # En kötü vardiya
        worst_shift = min(shift_analysis.items(), key=lambda x: x[1]['cpk'])
        if worst_shift[1]['cpk'] < 1.00:
            report['key_findings'].append(f"{worst_shift[0]} vardiyası düşük performans gösteriyor")
        
        # Öneriler
        if improvement['improvement_needed']['for_cpk_1.33']['sigma_reduction_%'] > 10:
            report['recommendations'].append("Varyasyon azaltma projesi başlatın (DMAIC)")
        
        if abs(main_cap['statistics']['mean'] - main_cap['statistics']['target']) > 2:
            report['recommendations'].append("Süreç ortalamasını hedefe kaydırın")
        
        return report


# TEST KODU
if __name__ == "__main__":
    print("=== SÜREÇ YETERLİLİK ANALİZİ ===\n")
    
    cap_analyzer = ProcessCapability()
    
    # 1. Ana yeterlilik analizi
    print("1. Toplam Üretim Süresi Yeterliliği:")
    main_cap = cap_analyzer.calculate_capability_indices('Toplam_Uretim_Suresi')
    print(f"   Cp: {main_cap['indices']['Cp']}")
    print(f"   Cpk: {main_cap['indices']['Cpk']}")
    print(f"   Sigma Seviyesi: {main_cap['sigma_level']}")
    print(f"   Beklenen PPM: {main_cap['ppm']['expected_total']}")
    print(f"   Durum: {main_cap['interpretation']['capability_status']}")
    
    # 2. Vardiya bazlı analiz
    print("\n2. Vardiya Bazlı Yeterlilik:")
    shift_results = cap_analyzer.analyze_by_shift()
    for shift, results in shift_results.items():
        print(f"   {shift}: Cpk={results['cpk']} ({results['performance']})")
    
    # 3. İyileştirme analizi
    print("\n3. İyileştirme İhtiyacı:")
    improvement = cap_analyzer.capability_improvement_analysis()
    print(f"   Cpk 1.33 için gereken sigma azaltımı: %{improvement['improvement_needed']['for_cpk_1.33']['sigma_reduction_%']}")
    print(f"   Beklenen hata azalması: %{improvement['expected_benefits']['defect_reduction_%']}")
    
    # 4. Genel rapor
    print("\n4. GENEL DURUM:")
    report = cap_analyzer.generate_capability_report()
    print(f"   {report['executive_summary']['capability_status']}")