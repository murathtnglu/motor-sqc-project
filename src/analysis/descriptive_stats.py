"""
Tanımlayıcı istatistikler modülü
Veri keşfi, özet istatistikler, dağılım analizi
"""

import pandas as pd
import numpy as np
from scipy import stats
import sys
import os

# Parent path'leri ekle (modül import'ları için)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader
from src.utils.statistics import StatisticalCalculator

class DescriptiveAnalysis:
    """Tanımlayıcı istatistik analizleri"""
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        self.stat_calc = StatisticalCalculator()
        
    def get_basic_stats(self):
        """
        Temel istatistikleri hesaplar
        """
        numeric_cols = [
            'Aktif_Calisma_Saat', 
            'Durma_Suresi_Saat',
            'KK_Hazirlik_Saat',
            'KK_Surec_Saat',
            'Toplam_Uretim_Suresi',
            'Verimlilik'
        ]
        
        stats_dict = {}
        
        for col in numeric_cols:
            if col in self.df.columns:
                stats_dict[col] = {
                    'ortalama': round(self.df[col].mean(), 2),
                    'medyan': round(self.df[col].median(), 2),
                    'std_sapma': round(self.df[col].std(), 2),
                    'varyans': round(self.df[col].var(), 2),
                    'min': round(self.df[col].min(), 2),
                    'max': round(self.df[col].max(), 2),
                    'q1': round(self.df[col].quantile(0.25), 2),
                    'q3': round(self.df[col].quantile(0.75), 2),
                    'iqr': round(self.df[col].quantile(0.75) - self.df[col].quantile(0.25), 2),
                    'carpiklik': round(self.df[col].skew(), 2),
                    'basiklik': round(self.df[col].kurtosis(), 2),
                    'cv': round((self.df[col].std() / self.df[col].mean()) * 100, 2)  # Varyasyon katsayısı
                }
        
        return stats_dict
    
    def detect_outliers(self, column, method='iqr'):
        """
        Aykırı değerleri tespit eder
        
        Args:
            column: Analiz edilecek sütun
            method: 'iqr' veya 'zscore'
        """
        data = self.df[column]
        
        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = self.df[(data < lower_bound) | (data > upper_bound)]
            
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(data))
            outliers = self.df[z_scores > 3]
            
        return {
            'outlier_count': len(outliers),
            'outlier_percentage': round((len(outliers) / len(self.df)) * 100, 2),
            'outlier_indices': outliers.index.tolist(),
            'outlier_values': outliers[column].tolist() if len(outliers) > 0 else []
        }
    
    def normality_test(self, column):
        """
        Normallik testi yapar (Shapiro-Wilk ve Anderson-Darling)
        """
        data = self.df[column].dropna()
        
        # Shapiro-Wilk testi (n<5000 için)
        if len(data) < 5000:
            shapiro_stat, shapiro_p = stats.shapiro(data)
        else:
            shapiro_stat, shapiro_p = None, None
            
        # Anderson-Darling testi
        anderson_result = stats.anderson(data, dist='norm')
        
        # Kolmogorov-Smirnov testi
        ks_stat, ks_p = stats.kstest(data, 'norm', args=(data.mean(), data.std()))
        
        return {
            'shapiro': {
                'statistic': round(shapiro_stat, 4) if shapiro_stat else None,
                'p_value': round(shapiro_p, 4) if shapiro_p else None,
                'is_normal': shapiro_p > 0.05 if shapiro_p else None
            },
            'anderson': {
                'statistic': round(anderson_result.statistic, 4),
                'critical_values': anderson_result.critical_values.tolist(),
                'significance_levels': anderson_result.significance_level.tolist()
            },
            'kolmogorov_smirnov': {
                'statistic': round(ks_stat, 4),
                'p_value': round(ks_p, 4),
                'is_normal': ks_p > 0.05
            }
        }
    
    def get_correlation_analysis(self):
        """
        Korelasyon analizi yapar
        """
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        # Pearson korelasyon
        pearson_corr = self.df[numeric_cols].corr(method='pearson')
        
        # Spearman korelasyon (rank-based)
        spearman_corr = self.df[numeric_cols].corr(method='spearman')
        
        # En güçlü korelasyonları bul
        strong_correlations = []
        for i in range(len(pearson_corr.columns)):
            for j in range(i+1, len(pearson_corr.columns)):
                corr_value = pearson_corr.iloc[i, j]
                if abs(corr_value) > 0.5 and abs(corr_value) < 1:
                    strong_correlations.append({
                        'var1': pearson_corr.columns[i],
                        'var2': pearson_corr.columns[j],
                        'correlation': round(corr_value, 3)
                    })
        
        return {
            'pearson': pearson_corr.round(3).to_dict(),
            'spearman': spearman_corr.round(3).to_dict(),
            'strong_correlations': strong_correlations
        }
    
    def get_distribution_analysis(self, column):
        """
        Dağılım analizi yapar
        """
        data = self.df[column]
        
        # Histogram için bin sayısı (Sturges' rule)
        n_bins = int(np.ceil(np.log2(len(data)) + 1))
        
        # Histogram verileri
        hist, bin_edges = np.histogram(data, bins=n_bins)
        
        # Dağılım özellikleri
        return {
            'histogram': {
                'counts': hist.tolist(),
                'bin_edges': bin_edges.tolist(),
                'n_bins': n_bins
            },
            'distribution_shape': {
                'mean': round(data.mean(), 2),
                'median': round(data.median(), 2),
                'mode': round(data.mode().iloc[0], 2) if not data.mode().empty else None,
                'skewness': round(data.skew(), 2),
                'kurtosis': round(data.kurtosis(), 2),
                'interpretation': self._interpret_distribution(data.skew(), data.kurtosis())
            }
        }
    
    def _interpret_distribution(self, skew, kurt):
        """
        Çarpıklık ve basıklık yorumlama
        """
        interpretation = []
        
        # Çarpıklık yorumu
        if abs(skew) < 0.5:
            interpretation.append("Simetrik dağılım")
        elif skew > 0.5:
            interpretation.append("Sağa çarpık (pozitif çarpık)")
        else:
            interpretation.append("Sola çarpık (negatif çarpık)")
            
        # Basıklık yorumu
        if abs(kurt) < 0.5:
            interpretation.append("Normal basıklık (mesokurtic)")
        elif kurt > 0.5:
            interpretation.append("Sivri dağılım (leptokurtic)")
        else:
            interpretation.append("Basık dağılım (platykurtic)")
            
        return ", ".join(interpretation)
    
    def get_time_based_analysis(self):
        """
        Zaman bazlı trend analizi
        """
        # Günlük ortalamalar
        daily_stats = self.df.groupby('Tarih').agg({
            'Verimlilik': 'mean',
            'Toplam_Uretim_Suresi': 'mean',
            'Hatali': 'sum',
            'Motor_ID': 'count'
        }).round(2)
        
        daily_stats.columns = ['Ort_Verimlilik', 'Ort_Toplam_Sure', 'Hata_Sayisi', 'Uretim_Adedi']
        
        # Trend analizi (lineer regresyon)
        x = np.arange(len(daily_stats))
        y = daily_stats['Ort_Verimlilik'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            'daily_stats': daily_stats.to_dict('index'),
            'trend': {
                'slope': round(slope, 4),
                'direction': 'Artan' if slope > 0 else 'Azalan',
                'r_squared': round(r_value**2, 4),
                'p_value': round(p_value, 4),
                'trend_significance': 'Anlamlı' if p_value < 0.05 else 'Anlamsız'
            }
        }
    
    def generate_summary_report(self):
        """
        Özet rapor oluşturur
        """
        report = {
            'genel_bilgiler': {
                'toplam_motor': len(self.df),
                'tarih_araligi': f"{self.df['Tarih'].min()} - {self.df['Tarih'].max()}",
                'vardiya_dagilimi': self.df['Vardiya'].value_counts().to_dict(),
                'hata_orani': f"{(self.df['Hatali'].mean() * 100):.1f}%"
            },
            'verimlilik_ozeti': {
                'ortalama': f"{self.df['Verimlilik'].mean():.2f}%",
                'std_sapma': f"{self.df['Verimlilik'].std():.2f}%",
                'min': f"{self.df['Verimlilik'].min():.2f}%",
                'max': f"{self.df['Verimlilik'].max():.2f}%"
            },
            'kritik_bulgular': [],
            'oneriler': []
        }
        
        # Kritik bulguları ekle
        if self.df['Verimlilik'].mean() < 85:
            report['kritik_bulgular'].append("Verimlilik hedefin altında")
            
        if self.df['Hatali'].mean() > 0.05:
            report['kritik_bulgular'].append("Hata oranı kabul edilebilir seviyenin üzerinde")
            
        # Önerileri ekle
        if self.df['Durma_Suresi_Saat'].mean() > 2:
            report['oneriler'].append("Plansız duruşları azaltmak için bakım programı gözden geçirilmeli")
            
        return report


# TEST KODU
if __name__ == "__main__":
    print("=== TANIMLAYıCı İSTATİSTİK ANALİZİ ===\n")
    
    analyzer = DescriptiveAnalysis()
    
    # Temel istatistikler
    print("1. Temel İstatistikler:")
    basic_stats = analyzer.get_basic_stats()
    for col, stats in list(basic_stats.items())[:2]:  # İlk 2 değişken
        print(f"\n{col}:")
        print(f"  Ortalama: {stats['ortalama']}")
        print(f"  Std Sapma: {stats['std_sapma']}")
        print(f"  Min-Max: {stats['min']} - {stats['max']}")
    
    # Normallik testi
    print("\n2. Normallik Testi (Toplam Üretim Süresi):")
    norm_test = analyzer.normality_test('Toplam_Uretim_Suresi')
    print(f"  Shapiro p-değeri: {norm_test['shapiro']['p_value']}")
    print(f"  Normal mi?: {norm_test['shapiro']['is_normal']}")
    
    # Özet rapor
    print("\n3. Özet Rapor:")
    report = analyzer.generate_summary_report()
    print(f"  Toplam Motor: {report['genel_bilgiler']['toplam_motor']}")
    print(f"  Ortalama Verimlilik: {report['verimlilik_ozeti']['ortalama']}")