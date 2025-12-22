"""
Veri yükleme ve işleme modülü
Bu modül:
1. Excel'den veriyi okur
2. Veri temizleme ve dönüşüm yapar
3. Türetilmiş değişkenler oluşturur (verimlilik, OEE vb.)
4. Dashboard için JSON formatına çevirir
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class DataLoader:
    """Motor üretim verilerini yükleyen ve işleyen ana sınıf"""
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Excel dosyasının yolu
        """
        self.data_path = data_path
        self.df = None  # Ham veri
        self.processed_df = None  # İşlenmiş veri
        
    def load_data(self):
        """
        Excel dosyasından veriyi yükler ve otomatik işler
        Returns:
            pd.DataFrame: İşlenmiş veri
        """
        try:
            # Excel'i oku
            self.df = pd.read_excel(self.data_path)
            print(f"✓ Veri yüklendi: {len(self.df)} kayıt")
            
            # Veriyi işle
            self._preprocess_data()
            return self.processed_df
            
        except FileNotFoundError:
            print(f"❌ Dosya bulunamadı: {self.data_path}")
            return None
        except Exception as e:
            print(f"❌ Veri yükleme hatası: {str(e)}")
            return None
    
    def _preprocess_data(self):
        """
        Veri ön işleme adımları
        - Tarih formatı düzenleme
        - Türetilmiş değişkenler oluşturma
        - Hesaplamalar
        """
        df = self.df.copy()
        
        # 1. TARİH DÖNÜŞÜMÜ
        # Excel'deki '01.11.2025' formatını datetime'a çevir
        df['Tarih'] = pd.to_datetime(df['Tarih'], format='%d.%m.%Y')
        
        # 2. MOTOR NUMARASI ÇIKARMA
        # BMC-1001 → 1001
        df['Motor_No'] = df['Motor_ID'].str.extract(r'(\d+)').astype(int)
        
        # 3. VERİMLİLİK HESAPLAMA
        # Verimlilik = (Aktif Çalışma / Toplam Süre) × 100
        df['Verimlilik'] = (df['Aktif_Calisma_Saat'] / 
                            df['Toplam_Uretim_Suresi']) * 100
        
        # 4. TOPLAM KAYIP SÜRESİ
        # Kayıp = Durma + KK Hazırlık + KK Süreç
        df['Toplam_Kayip'] = (df['Durma_Suresi_Saat'] + 
                              df['KK_Hazirlik_Saat'] + 
                              df['KK_Surec_Saat'])
        
        # 5. HATA DURUMU (Binary)
        # Hata var mı? (1: Evet, 0: Hayır)
        df['Hatali'] = (df['Hata_Nedeni'] != '-').astype(int)
        
        # 6. VARDİYA NUMARALANDIRMASI
        vardiya_map = {
            '08:00-16:00': 1,  # Sabah
            '16:00-24:00': 2,  # Akşam  
            '24:00-08:00': 3   # Gece
        }
        df['Vardiya_No'] = df['Vardiya'].map(vardiya_map)
        
        # 7. ZAMAN ANALİZİ İÇİN EK ALANLAR
        df['Hafta_Gunu'] = df['Tarih'].dt.day_name()
        df['Gun'] = df['Tarih'].dt.day
        df['Hafta'] = df['Tarih'].dt.isocalendar().week
        
        # 8. GÜNLÜK ÜRETİM SIRASI
        # Her gün içinde kaçıncı motor?
        df['Gunluk_Sira'] = df.groupby('Tarih').cumcount() + 1
        
        # 9. KONTROL GRAFİKLERİ İÇİN MOVING RANGE
        # Ardışık gözlemler arası fark
        df['Moving_Range'] = df['Toplam_Uretim_Suresi'].diff().abs()
        
        # 10. OEE BİLEŞENLERİ
        # Kullanılabilirlik = (Toplam - Durma) / Toplam
        df['Kullanilabilirlik'] = ((df['Toplam_Uretim_Suresi'] - 
                                    df['Durma_Suresi_Saat']) / 
                                   df['Toplam_Uretim_Suresi']) * 100
        
        # Kalite = 1 (hatalı) veya 0 (hatasız) → tersini al
        df['Kalite_Puani'] = (1 - df['Hatali']) * 100
        
        self.processed_df = df
        print(f"✓ Veri işlendi: {len(df.columns)} değişken")
        
    def get_summary_stats(self):
        """
        Özet istatistikleri hesaplar
        Dashboard'un üst kısmındaki KPI kartları için
        """
        if self.processed_df is None:
            self.load_data()
            
        df = self.processed_df
        
        return {
            # TEMEL METRİKLER
            'toplam_motor': len(df),
            'tarih_araligi': f"{df['Tarih'].min().strftime('%d.%m.%Y')} - {df['Tarih'].max().strftime('%d.%m.%Y')}",
            
            # HATA ANALİZİ
            'hatali_motor': df['Hatali'].sum(),
            'hata_orani': round(df['Hatali'].mean() * 100, 1),
            
            # VERİMLİLİK
            'ortalama_verimlilik': round(df['Verimlilik'].mean(), 2),
            'min_verimlilik': round(df['Verimlilik'].min(), 2),
            'max_verimlilik': round(df['Verimlilik'].max(), 2),
            
            # SÜRE ANALİZİ (Ortalama)
            'ort_toplam_sure': round(df['Toplam_Uretim_Suresi'].mean(), 2),
            'ort_aktif_sure': round(df['Aktif_Calisma_Saat'].mean(), 2),
            'ort_durma': round(df['Durma_Suresi_Saat'].mean(), 2),
            'ort_kk_hazirlik': round(df['KK_Hazirlik_Saat'].mean(), 2),
            'ort_kk_surec': round(df['KK_Surec_Saat'].mean(), 2),
            'ort_toplam_kayip': round(df['Toplam_Kayip'].mean(), 2),
            
            # SÜRE ANALİZİ (Toplam)
            'toplam_uretim_suresi': round(df['Toplam_Uretim_Suresi'].sum(), 1),
            'toplam_aktif_sure': round(df['Aktif_Calisma_Saat'].sum(), 1),
            'toplam_durma': round(df['Durma_Suresi_Saat'].sum(), 1),
            'toplam_kk_hazirlik': round(df['KK_Hazirlik_Saat'].sum(), 1),
            'toplam_kk_surec': round(df['KK_Surec_Saat'].sum(), 1),
            
            # OEE
            'ort_kullanilabilirlik': round(df['Kullanilabilirlik'].mean(), 1),
            'kalite_orani': round(df['Kalite_Puani'].mean(), 1),
            'oee': round(df['Kullanilabilirlik'].mean() * 
                        df['Kalite_Puani'].mean() / 100, 1)
        }
    
    def get_pareto_data(self):
        """
        Pareto analizi için veri hazırlar
        Hata türlerini sıklığa göre sıralar
        """
        if self.processed_df is None:
            self.load_data()
            
        # Sadece hatalı motorları al
        hata_df = self.processed_df[self.processed_df['Hata_Nedeni'] != '-']
        
        if len(hata_df) == 0:
            return pd.DataFrame()
        
        # Hata türlerini say ve sırala
        pareto = (hata_df.groupby('Hata_Nedeni')
                  .size()
                  .sort_values(ascending=False)
                  .reset_index(name='Adet'))
        
        # Yüzde ve kümülatif yüzde hesapla
        pareto['Yuzde'] = (pareto['Adet'] / pareto['Adet'].sum()) * 100
        pareto['Kumulatif_Yuzde'] = pareto['Yuzde'].cumsum()
        
        # Pareto kategorisi (80/20 kuralı)
        pareto['Kategori'] = pareto['Kumulatif_Yuzde'].apply(
            lambda x: 'Hayati Azınlık' if x <= 80 else 'Önemsiz Çoğunluk'
        )
        
        return pareto
    
    def get_vardiya_performance(self):
        """
        Vardiya bazlı performans karşılaştırması
        """
        if self.processed_df is None:
            self.load_data()
            
        return self.processed_df.groupby('Vardiya').agg({
            'Motor_ID': 'count',  # Üretim adedi
            'Verimlilik': ['mean', 'std'],
            'Toplam_Uretim_Suresi': ['mean', 'std'],
            'Aktif_Calisma_Saat': 'mean',
            'Durma_Suresi_Saat': 'mean',
            'Hatali': ['sum', lambda x: x.mean() * 100]  # Hata sayısı ve oranı
        }).round(2)
    
    def get_time_series_data(self):
        """
        Zaman serisi analizi için günlük agregasyon
        """
        if self.processed_df is None:
            self.load_data()
            
        return self.processed_df.groupby('Tarih').agg({
            'Motor_ID': 'count',
            'Verimlilik': 'mean',
            'Toplam_Uretim_Suresi': 'mean',
            'Hatali': 'sum'
        }).reset_index()
    
    def export_to_csv(self):
        """
        İşlenmiş veriyi CSV olarak kaydet
        """
        if self.processed_df is None:
            self.load_data()
            
        output_path = 'data/processed/motor_data_cleaned.csv'
        self.processed_df.to_csv(output_path, index=False)
        print(f"✓ CSV kaydedildi: {output_path}")
        return True
    
    def get_json_for_dashboard(self):
        """
        Dashboard (HTML/JavaScript) için JSON formatında tüm veriyi döndür
        """
        if self.processed_df is None:
            self.load_data()
        
        # Tarih sütununu JSON serialize edilebilir yap
        json_df = self.processed_df.copy()
        json_df['Tarih'] = json_df['Tarih'].dt.strftime('%Y-%m-%d')
        
        return {
            'raw_data': json_df.to_dict('records'),
            'summary': self.get_summary_stats(),
            'pareto': self.get_pareto_data().to_dict('records') if not self.get_pareto_data().empty else [],
            'vardiya': self.get_vardiya_performance().to_dict(),
            'time_series': self.get_time_series_data().to_dict('records'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# TEST KODU - Modülü test etmek için
if __name__ == "__main__":
    # DataLoader'ı başlat
    loader = DataLoader()
    
    # Veriyi yükle
    df = loader.load_data()
    
    if df is not None:
        print("\n=== ÖZET İSTATİSTİKLER ===")
        stats = loader.get_summary_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        print("\n=== PARETO ANALİZİ ===")
        print(loader.get_pareto_data())
        
        print("\n=== VARDİYA PERFORMANSI ===")
        print(loader.get_vardiya_performance())
        
        # CSV'ye kaydet
        loader.export_to_csv()