import os
import sys
import subprocess
from datetime import datetime

def run_demo():
    print("="*50)
    print(f"🚀 MOTOR ÜRETİM SQC SİSTEMİ BAŞLATILIYOR")
    print(f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*50)

    # 1. Adım: Dashboard Verisini Güncelle
    print("\n[1/3] 📊 Analizler yapılıyor ve JSON üretiliyor...")
    try:
        from src.visualization.dashboard import Dashboard
        db = Dashboard()
        db.export_dashboard_json(output_path='app/dashboard_data.json')
        print("✅ Analizler tamamlandı, dashboard_data.json güncellendi.")
    except Exception as e:
        print(f"❌ Analiz hatası: {e}")
        return

    # 2. Adım: Raporları Üret
    print("\n[2/3] 📝 Yönetici raporları oluşturuluyor...")
    try:
        from src.visualization.reports import ReportGenerator
        rg = ReportGenerator()
        rg.generate_all_reports()
        print("✅ Raporlar 'reports/' klasörüne kaydedildi.")
    except Exception as e:
        print(f"❌ Raporlama hatası: {e}")

    # 3. Adım: Arayüzü Başlat
    print("\n[3/3] 🌐 Arayüz ayağa kaldırılıyor...")
    print("👉 Tarayıcınızda şu adresi açın: http://localhost:8000")
    print("🔴 Durdurmak için: Ctrl+C")
    
    try:
        # Python'ın yerleşik HTTP sunucusunu başlatır (Daha güvenilir yöntem)
        subprocess.run(["python", "-m", "http.server", "8000"])
    except KeyboardInterrupt:
        print("\n👋 Sistem kapatıldı.")

if __name__ == "__main__":
    run_demo()