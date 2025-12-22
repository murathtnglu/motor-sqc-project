"""
Pareto Analizi Modülü
80/20 kuralı ile hata ve kayıp analizleri
"""

import pandas as pd
import numpy as np
import sys
import os

# Path ayarlaması
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader

class ParetoAnalysis:
    """
    Pareto prensibi ile kritik problemleri belirleme
    - Hata türleri analizi
    - Zaman kayıpları analizi
    - Maliyet bazlı analiz
    """
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Veri dosyası yolu
        """
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        
    def analyze_defects(self):
        """
        Hata türlerinin Pareto analizi
        
        Returns:
            dict: Hata analizi sonuçları
        """
        # Sadece hatalı motorları al
        defects_df = self.df[self.df['Hata_Nedeni'] != '-'].copy()
        
        if len(defects_df) == 0:
            return {
                'data': [],
                'summary': {'toplam_hata_sayisi': 0},
                'recommendations': []
            }
        
        # Hata türlerini sayarak Pareto tablosu oluştur
        pareto_df = (defects_df.groupby('Hata_Nedeni')
                     .size()
                     .sort_values(ascending=False)
                     .reset_index(name='Adet'))
        
        # Sütun adını değiştir
        pareto_df.rename(columns={'Hata_Nedeni': 'Hata_Turu'}, inplace=True)
        
        # Toplam hata sayısı
        total_defects = pareto_df['Adet'].sum()
        
        # Yüzde hesapla
        pareto_df['Yuzde'] = (pareto_df['Adet'] / total_defects) * 100
        
        # Kümülatif yüzde
        pareto_df['Kumulatif_Yuzde'] = pareto_df['Yuzde'].cumsum()
        
        # Pareto kategorisi belirle
        pareto_df['Kategori'] = pareto_df['Kumulatif_Yuzde'].apply(
            lambda x: 'Hayati Azınlık (A)' if x <= 80 
            else 'Orta Önem (B)' if x <= 95 
            else 'Önemsiz Çoğunluk (C)'
        )
        
        # Her hata türü için ek analiz
        defect_details = {}
        for defect_type in pareto_df['Hata_Turu'].unique():
            defect_motors = defects_df[defects_df['Hata_Nedeni'] == defect_type]
            
            # DÜZELTME: date objelerini string'e dönüştür
            tarih_dagilimi_dict = defect_motors['Tarih'].dt.date.value_counts().to_dict()
            tarih_dagilimi_str = {str(k): v for k, v in tarih_dagilimi_dict.items()}
            
            defect_details[defect_type] = {
                'motor_ids': defect_motors['Motor_ID'].tolist(),
                'vardiya_dagilimi': defect_motors['Vardiya'].value_counts().to_dict(),
                'ortalama_uretim_suresi': round(defect_motors['Toplam_Uretim_Suresi'].mean(), 2),
                'tarih_dagilimi': tarih_dagilimi_str  # String'e dönüştürülmüş tarihler
            }
        
        # Hayati azınlık hataları
        vital_few = pareto_df[pareto_df['Kategori'] == 'Hayati Azınlık (A)']['Hata_Turu'].tolist()
        
        # Özet istatistikler
        summary = {
            'toplam_hata_sayisi': total_defects,
            'hata_cesidi_sayisi': len(pareto_df),
            'hata_orani': round((total_defects / len(self.df)) * 100, 1),
            'hayati_azinlik': vital_few,
            'hayati_azinlik_orani': round(
                pareto_df[pareto_df['Kategori'] == 'Hayati Azınlık (A)']['Yuzde'].sum(), 1
            ),
            'en_kritik_hata': pareto_df.iloc[0]['Hata_Turu'] if len(pareto_df) > 0 else None,
            'en_kritik_hata_orani': pareto_df.iloc[0]['Yuzde'] if len(pareto_df) > 0 else 0
        }
        
        return {
            'data': pareto_df.to_dict('records'),
            'details': defect_details,
            'summary': summary,
            'recommendations': self._generate_defect_recommendations(pareto_df, defect_details)
        }
    
    def _generate_defect_recommendations(self, pareto_df, defect_details):
        """
        Hata analizi sonuçlarına göre öneriler oluştur
        """
        recommendations = []
        
        if len(pareto_df) == 0:
            return recommendations
        
        # En kritik hatalar için öneriler
        for _, row in pareto_df.iterrows():
            if row['Kategori'] == 'Hayati Azınlık (A)':
                defect_type = row['Hata_Turu']
                detail = defect_details.get(defect_type, {})
                
                if 'Sızdırmazlık' in defect_type:
                    recommendations.append({
                        'hata': defect_type,
                        'oncelik': 'Kritik',
                        'aksiyon': 'Conta malzeme kalitesi ve montaj prosedürü gözden geçirilmeli',
                        'sorumlu': 'Kalite ve Üretim Müdürlüğü',
                        'beklenen_etki': 'Hata oranında %50 azalma',
                        'maliyet': 'Orta'
                    })
                    recommendations.append({
                        'hata': defect_type,
                        'oncelik': 'Kritik',
                        'aksiyon': 'Montaj operatörlerine sızdırmazlık konusunda eğitim verilmeli',
                        'sorumlu': 'İnsan Kaynakları ve Üretim',
                        'beklenen_etki': 'Montaj hatalarında %30 azalma',
                        'maliyet': 'Düşük'
                    })
                    
                elif 'Tork' in defect_type:
                    recommendations.append({
                        'hata': defect_type,
                        'oncelik': 'Yüksek',
                        'aksiyon': 'Tork tabancalarının kalibrasyonu günlük yapılmalı',
                        'sorumlu': 'Bakım Müdürlüğü',
                        'beklenen_etki': 'Tork hatalarında %70 azalma',
                        'maliyet': 'Düşük'
                    })
                    
                elif 'Çatlak' in defect_type or 'Yüzey' in defect_type:
                    recommendations.append({
                        'hata': defect_type,
                        'oncelik': 'Orta',
                        'aksiyon': 'Görsel kontrol prosedürü revize edilmeli, ışık sistemi iyileştirilmeli',
                        'sorumlu': 'Kalite Güvence',
                        'beklenen_etki': 'Yüzey hatası tespitinde %40 iyileşme',
                        'maliyet': 'Orta'
                    })
                    
        return recommendations
    
    def analyze_time_losses(self):
        """
        Zaman kayıplarının Pareto analizi
        
        Returns:
            dict: Zaman kayıpları analizi
        """
        # Zaman kayıp kategorileri
        time_losses = {
            'Plansız Duruşlar': self.df['Durma_Suresi_Saat'].sum(),
            'KK Hazırlık Beklemesi': self.df['KK_Hazirlik_Saat'].sum(),
            'KK Süreç Beklemesi': self.df['KK_Surec_Saat'].sum()
        }
        
        # Pareto tablosu oluştur
        pareto_df = pd.DataFrame(
            list(time_losses.items()),
            columns=['Kayip_Turu', 'Toplam_Saat']
        ).sort_values('Toplam_Saat', ascending=False)
        
        total_loss = pareto_df['Toplam_Saat'].sum()
        
        # Yüzde ve kümülatif hesapla
        pareto_df['Yuzde'] = (pareto_df['Toplam_Saat'] / total_loss) * 100
        pareto_df['Kumulatif_Yuzde'] = pareto_df['Yuzde'].cumsum()
        
        # Kritiklik seviyesi
        pareto_df['Kritiklik'] = pareto_df['Kumulatif_Yuzde'].apply(
            lambda x: 'Kritik' if x <= 50 else 'Orta' if x <= 80 else 'Düşük'
        )
        
        # Kayıp detayları
        loss_details = {
            'Plansız Duruşlar': {
                'ortalama_saat': round(self.df['Durma_Suresi_Saat'].mean(), 2),
                'max_saat': round(self.df['Durma_Suresi_Saat'].max(), 2),
                'etkilenen_motor_sayisi': (self.df['Durma_Suresi_Saat'] > 0).sum(),
                'tahmini_maliyet': round(time_losses['Plansız Duruşlar'] * 500, 0)  # Saat başı 500 TL
            },
            'KK Hazırlık Beklemesi': {
                'ortalama_saat': round(self.df['KK_Hazirlik_Saat'].mean(), 2),
                'max_saat': round(self.df['KK_Hazirlik_Saat'].max(), 2),
                'etkilenen_motor_sayisi': (self.df['KK_Hazirlik_Saat'] > 0).sum(),
                'tahmini_maliyet': round(time_losses['KK Hazırlık Beklemesi'] * 300, 0)
            },
            'KK Süreç Beklemesi': {
                'ortalama_saat': round(self.df['KK_Surec_Saat'].mean(), 2),
                'max_saat': round(self.df['KK_Surec_Saat'].max(), 2),
                'etkilenen_motor_sayisi': (self.df['KK_Surec_Saat'] > 0).sum(),
                'tahmini_maliyet': round(time_losses['KK Süreç Beklemesi'] * 350, 0)
            }
        }
        
        return {
            'data': pareto_df.to_dict('records'),
            'details': loss_details,
            'summary': {
                'toplam_kayip_saat': round(total_loss, 1),
                'ort_motor_basi_kayip': round(total_loss / len(self.df), 2),
                'tahmini_toplam_maliyet': sum(d['tahmini_maliyet'] for d in loss_details.values())
            },
            'recommendations': self._generate_time_loss_recommendations(pareto_df, loss_details)
        }
    
    def _generate_time_loss_recommendations(self, pareto_df, loss_details):
        """
        Zaman kayıpları için öneriler
        """
        recommendations = []
        
        for _, row in pareto_df.iterrows():
            kayip_turu = row['Kayip_Turu']
            
            if 'KK Süreç' in kayip_turu and row['Kritiklik'] == 'Kritik':
                recommendations.append({
                    'kayip': kayip_turu,
                    'oncelik': 'Kritik',
                    'aksiyon': 'KK süreçlerinde otomasyon veya inline ölçüm sistemleri değerlendirilmeli',
                    'beklenen_etki': f"KK süresinde %30 azalma ({row['Toplam_Saat'] * 0.3:.0f} saat tasarruf)",
                    'yatirim': 'Yüksek',
                    'geri_donus': '6-8 ay'
                })
                
            elif 'KK Hazırlık' in kayip_turu:
                recommendations.append({
                    'kayip': kayip_turu,
                    'oncelik': 'Yüksek',
                    'aksiyon': 'KK hazırlık süreci SMED metodolojisi ile optimize edilmeli',
                    'beklenen_etki': f"Hazırlık süresinde %40 azalma",
                    'yatirim': 'Orta',
                    'geri_donus': '3-4 ay'
                })
                
            elif 'Plansız' in kayip_turu:
                recommendations.append({
                    'kayip': kayip_turu,
                    'oncelik': 'Orta',
                    'aksiyon': 'Önleyici bakım programı güçlendirilmeli, kritik ekipmanlar belirlenmeli',
                    'beklenen_etki': f"Duruşlarda %25 azalma",
                    'yatirim': 'Orta',
                    'geri_donus': '4-6 ay'
                })
                
        return recommendations
    
    def analyze_combined_losses(self):
        """
        Hata ve zaman kayıplarının birleşik analizi
        Maliyet bazında önceliklendirme
        
        Returns:
            dict: Birleşik kayıp analizi
        """
        # Hata maliyetleri (tahmini)
        defect_costs = {}
        defects_df = self.df[self.df['Hata_Nedeni'] != '-']
        
        for defect_type in defects_df['Hata_Nedeni'].unique():
            count = (defects_df['Hata_Nedeni'] == defect_type).sum()
            
            # Hata türüne göre tahmini birim maliyet
            if 'Sızdırmazlık' in defect_type:
                unit_cost = 5000  # TL
            elif 'Tork' in defect_type:
                unit_cost = 3000
            elif 'Yüzey' in defect_type or 'Çatlak' in defect_type:
                unit_cost = 4000
            else:
                unit_cost = 2000
                
            defect_costs[f"Hata: {defect_type}"] = count * unit_cost
        
        # Zaman kaybı maliyetleri
        time_costs = {
            'Plansız Duruşlar': self.df['Durma_Suresi_Saat'].sum() * 500,
            'KK Hazırlık': self.df['KK_Hazirlik_Saat'].sum() * 300,
            'KK Süreç': self.df['KK_Surec_Saat'].sum() * 350
        }
        
        # Tüm maliyetleri birleştir
        all_costs = {**defect_costs, **time_costs}
        
        # Pareto tablosu
        combined_df = pd.DataFrame(
            list(all_costs.items()),
            columns=['Kayip_Turu', 'Maliyet_TL']
        ).sort_values('Maliyet_TL', ascending=False)
        
        total_cost = combined_df['Maliyet_TL'].sum()
        
        combined_df['Yuzde'] = (combined_df['Maliyet_TL'] / total_cost) * 100
        combined_df['Kumulatif_Yuzde'] = combined_df['Yuzde'].cumsum()
        
        # Öncelik sınıflandırması
        combined_df['Oncelik'] = combined_df.apply(
            lambda row: 'P1' if row['Kumulatif_Yuzde'] <= 50
            else 'P2' if row['Kumulatif_Yuzde'] <= 80
            else 'P3' if row['Kumulatif_Yuzde'] <= 95
            else 'P4', axis=1
        )
        
        # Özet
        summary = {
            'toplam_maliyet': round(total_cost, 0),
            'motor_basi_maliyet': round(total_cost / len(self.df), 0),
            'en_kritik_kayip': combined_df.iloc[0]['Kayip_Turu'] if len(combined_df) > 0 else None,
            'en_kritik_maliyet': round(combined_df.iloc[0]['Maliyet_TL'], 0) if len(combined_df) > 0 else 0,
            'p1_kayip_sayisi': (combined_df['Oncelik'] == 'P1').sum(),
            'p1_maliyet_orani': round(combined_df[combined_df['Oncelik'] == 'P1']['Yuzde'].sum(), 1)
        }
        
        return {
            'data': combined_df.to_dict('records'),
            'summary': summary,
            'cost_breakdown': {
                'defect_costs': sum(defect_costs.values()),
                'time_loss_costs': sum(time_costs.values()),
                'ratio': round(sum(defect_costs.values()) / sum(time_costs.values()), 2) if sum(time_costs.values()) > 0 else 0
            }
        }
    
    def generate_pareto_report(self):
        """
        Kapsamlı Pareto raporu oluştur
        
        Returns:
            dict: Özet rapor
        """
        defects = self.analyze_defects()
        time_losses = self.analyze_time_losses()
        combined = self.analyze_combined_losses()
        
        # En kritik 3 problem
        top_issues = []
        
        if defects['summary'].get('en_kritik_hata'):
            top_issues.append({
                'tip': 'Hata',
                'problem': defects['summary']['en_kritik_hata'],
                'etki': f"{defects['summary']['en_kritik_hata_orani']:.1f}% hata oranı",
                'oncelik': 'Kritik'
            })
        
        if len(time_losses['data']) > 0:
            top_time_loss = time_losses['data'][0]
            top_issues.append({
                'tip': 'Zaman Kaybı',
                'problem': top_time_loss['Kayip_Turu'],
                'etki': f"{top_time_loss['Toplam_Saat']:.0f} saat kayıp",
                'oncelik': top_time_loss['Kritiklik']
            })
        
        if len(combined['data']) > 0:
            top_cost = combined['data'][0]
            top_issues.append({
                'tip': 'Maliyet',
                'problem': top_cost['Kayip_Turu'],
                'etki': f"{top_cost['Maliyet_TL']:,.0f} TL",
                'oncelik': top_cost['Oncelik']
            })
        
        report = {
            'executive_summary': {
                'toplam_hata_orani': defects['summary'].get('hata_orani', 0),
                'toplam_zaman_kaybi': time_losses['summary'].get('toplam_kayip_saat', 0),
                'toplam_maliyet_kaybi': combined['summary'].get('toplam_maliyet', 0),
                'motor_basi_maliyet': combined['summary'].get('motor_basi_maliyet', 0)
            },
            'top_issues': top_issues[:3],  # En kritik 3 problem
            'vital_few': {
                'defects': defects['summary'].get('hayati_azinlik', []),
                'time_losses': [t['Kayip_Turu'] for t in time_losses['data'] if t.get('Kritiklik') == 'Kritik'],
                'cost_drivers': [c['Kayip_Turu'] for c in combined['data'] if c.get('Oncelik') == 'P1']
            },
            'improvement_potential': {
                'hata_azaltma': f"%{min(50, defects['summary'].get('hayati_azinlik_orani', 0))}",
                'zaman_kazanci': f"{time_losses['summary'].get('toplam_kayip_saat', 0) * 0.3:.0f} saat",
                'maliyet_tasarrufu': f"{combined['summary'].get('toplam_maliyet', 0) * 0.4:,.0f} TL"
            }
        }
        
        return report


# TEST KODU
if __name__ == "__main__":
    print("=== PARETO ANALİZİ ===\n")
    
    pareto = ParetoAnalysis()
    
    # 1. Hata analizi
    print("1. Hata Türleri Pareto Analizi:")
    defects = pareto.analyze_defects()
    for item in defects['data'][:3]:  # İlk 3 hata
        print(f"   {item['Hata_Turu']}: {item['Adet']} adet ({item['Yuzde']:.1f}%) - {item['Kategori']}")
    print(f"\n   Hayati Azınlık: {defects['summary']['hayati_azinlik']}")
    
    # 2. Zaman kayıpları
    print("\n2. Zaman Kayıpları Pareto Analizi:")
    time_losses = pareto.analyze_time_losses()
    for item in time_losses['data']:
        print(f"   {item['Kayip_Turu']}: {item['Toplam_Saat']:.0f} saat ({item['Yuzde']:.1f}%) - {item['Kritiklik']}")
    
    # 3. Maliyet analizi
    print("\n3. Maliyet Bazlı Kayıp Analizi:")
    combined = pareto.analyze_combined_losses()
    print(f"   Toplam Tahmini Maliyet: {combined['summary']['toplam_maliyet']:,.0f} TL")
    print(f"   Motor Başı Maliyet: {combined['summary']['motor_basi_maliyet']:,.0f} TL")
    print(f"   Top 3 Maliyet Kalemi: {[item['Kayip_Turu'] for item in combined['data'][:3]]}")
    
    # 4. Öneriler
    print("\n4. ÖNERİLER:")
    for i, rec in enumerate(defects['recommendations'][:3], 1):
        print(f"   {i}. [{rec['oncelik']}] {rec['aksiyon']}")
        print(f"      Beklenen Etki: {rec['beklenen_etki']}")