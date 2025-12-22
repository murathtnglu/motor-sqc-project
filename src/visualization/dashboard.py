"""
Ana Dashboard Modülü
Tüm analiz ve görselleştirmeleri birleştirir
"""

import pandas as pd
import numpy as np
import json
import sys
import os
from datetime import datetime, timedelta

# Path ayarlaması
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader
from src.utils.statistics import StatisticalCalculator
from src.analysis.descriptive_stats import DescriptiveAnalysis
from src.analysis.control_charts import ControlCharts
from src.analysis.capability_analysis import ProcessCapability
from src.analysis.pareto_analysis import ParetoAnalysis
from src.visualization.charts import ChartGenerator
# from src.visualization.reports import ReportGenerator  # KALDIRILDI - circular import

class Dashboard:
    """
    Ana dashboard sınıfı - tüm analiz ve görselleştirmeleri koordine eder
    """
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Excel veri dosyası yolu
        """
        self.data_path = data_path
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        
        # Analiz modülleri
        self.stat_calc = StatisticalCalculator()
        self.descriptive = DescriptiveAnalysis(data_path)
        self.control_charts = ControlCharts(data_path)
        self.capability = ProcessCapability(data_path)
        self.pareto = ParetoAnalysis(data_path)
        
        # Görselleştirme modülleri
        self.charts = ChartGenerator(data_path)
        # self.reports = ReportGenerator(data_path)  # KALDIRILDI - circular import
    
    def get_overview_data(self):
        """
        Dashboard ana sayfa (overview) verileri
        
        Returns:
            dict: KPI'lar, trendler, alertler
        """
        # KPI kartları
        kpis = self.charts.get_kpi_cards()
        
        # Son 7 gün trendi
        time_series = self.charts.get_time_series_chart()
        
        # Alertler
        alerts = self._generate_alerts()
        
        # Güncel durum
        current_status = self._get_current_shift_status()
        
        # Vardiya performansı - DÜZELTME: MultiIndex'i düzgün formata çevir
        shift_performance = self.loader.get_vardiya_performance()
        
        # MultiIndex DataFrame'i düz dictionary'e çevir
        shift_perf_dict = {}
        for idx in shift_performance.index:
            shift_perf_dict[idx] = {}
            for col in shift_performance.columns:
                # Tuple column'ları string'e çevir
                col_name = f"{col[0]}_{col[1]}" if isinstance(col, tuple) else str(col)
                shift_perf_dict[idx][col_name] = float(shift_performance.loc[idx, col]) if pd.notna(shift_performance.loc[idx, col]) else None
        
        return {
            'kpis': kpis,
            'time_series': time_series,
            'alerts': alerts,
            'current_status': current_status,
            'shift_performance': shift_perf_dict  # Düzeltilmiş format
        }
    
    def get_control_charts_data(self):
        """
        Kontrol grafikleri sayfası verileri
        
        Returns:
            dict: Shewhart, EWMA, CUSUM grafikleri ve analizleri
        """
        # X-bar ve R kontrol grafiği
        xbar_r_data = self.control_charts.create_xbar_r_chart('Toplam_Uretim_Suresi')
        
        # EWMA grafiği
        ewma_data = self.control_charts.create_ewma_chart('Verimlilik')
        
        # CUSUM grafiği
        cusum_data = self.control_charts.create_cusum_chart('Aktif_Calisma_Saat')
        
        # Kontrol dışı noktalar - TÜM KEYLER DÜZELTİLDİ
        out_of_control = {
            'xbar': xbar_r_data.get('xbar', {}).get('out_of_control', []) if 'xbar' in xbar_r_data else [],
            'ewma': ewma_data.get('out_of_control', []),  # Direkt out_of_control key'ini kullan
            'cusum': cusum_data.get('alarms', [])  # 'alarms' key'ini kullan
        }
        
        # Eğer EWMA için out_of_control yoksa, manuel hesapla
        if 'out_of_control' not in ewma_data and 'ewma_values' in ewma_data:
            ewma_out = []
            for i, val in enumerate(ewma_data['ewma_values']):
                if val > ewma_data['UCL'][i] or val < ewma_data['LCL'][i]:
                    ewma_out.append(i)
            out_of_control['ewma'] = ewma_out
        
        # Western Electric kuralları
        we_rules = self.control_charts.check_western_electric_rules('Aktif_Calisma_Saat')
        
        # Grafik verileri (Chart.js/Plotly formatında)
        xbar_chart = self.charts.get_control_chart_data('Toplam_Uretim_Suresi', 'shewhart')
        ewma_chart = self.charts.get_control_chart_data('Verimlilik', 'ewma')
        cusum_chart = self.charts.get_control_chart_data('Aktif_Calisma_Saat', 'cusum')
        
        # Özet rapor
        control_report = self.control_charts.generate_control_chart_report()
        
        return {
            'xbar_r': xbar_r_data,
            'ewma': {
                'data': ewma_data,
                'chart': ewma_chart
            },
            'cusum': {
                'data': cusum_data,
                'chart': cusum_chart
            },
            'out_of_control': out_of_control,
            'western_electric': we_rules,
            'report': control_report,
            'interpretation': self._interpret_control_charts(out_of_control)
        }
    
    def get_capability_data(self):
        """
        Süreç yeterliliği sayfası verileri
        
        Returns:
            dict: Cp, Cpk, Pp, Ppk ve diğer yeterlilik metrikleri
        """
        # Ana değişken için yeterlilik
        main_cap = self.capability.calculate_capability_indices('Toplam_Uretim_Suresi')
        
        # Tüm değişkenler için
        all_capabilities = self.capability.calculate_for_all_variables()
        
        # Vardiya bazlı yeterlilik
        shift_capability = self.capability.analyze_by_shift()
        
        # İyileştirme potansiyeli
        improvement = self.capability.capability_improvement_analysis()
        
        # Histogram ve dağılım
        histogram = self.charts.get_histogram_capability_data()
        
        return {
            'main_capability': main_cap,
            'all_variables': all_capabilities,
            'shift_analysis': shift_capability,
            'improvement_potential': improvement,
            'histogram': histogram,
            'recommendations': self._generate_capability_recommendations(main_cap)
        }
    
    def get_pareto_data(self):
        """
        Pareto analizi sayfası verileri
        
        Returns:
            dict: Pareto analizi verileri
        """
        # Hata analizi
        defects = self.pareto.analyze_defects()
        
        # Zaman kayıpları
        time_losses = self.pareto.analyze_time_losses()
        
        # Birleşik analiz
        combined = self.pareto.analyze_combined_losses()
        
        # Grafik verileri
        pareto_chart = self.charts.get_pareto_chart_data()
        
        # Özet rapor
        pareto_report = self.pareto.generate_pareto_report()
        
        return {
            'defect_analysis': defects,
            'time_loss_analysis': time_losses,
            'combined_analysis': combined,
            'chart': pareto_chart,
            'report': pareto_report,
            'action_priority': self._prioritize_actions(pareto_report)
        }
    
    def get_oee_data(self):
        """
        OEE dashboard verileri
        
        Returns:
            dict: OEE metrikleri ve analizleri
        """
        # OEE bileşenleri
        oee_components = self.stat_calc.calculate_oee_components(self.df)
        
        # Günlük OEE trendi
        daily_oee = []
        for date in self.df['Tarih'].unique():
            day_data = self.df[self.df['Tarih'] == date]
            day_oee = self.stat_calc.calculate_oee_components(day_data)
            daily_oee.append({
                'date': date.strftime('%Y-%m-%d'),
                'oee': day_oee['oee'],
                'availability': day_oee['availability'],
                'performance': day_oee['performance'],
                'quality': day_oee['quality']
            })
        
        # Waterfall chart
        waterfall = self.charts.get_oee_waterfall_chart()
        
        # Vardiya OEE karşılaştırması
        shift_oee = {}
        for shift in self.df['Vardiya'].unique():
            shift_data = self.df[self.df['Vardiya'] == shift]
            shift_oee[shift] = self.stat_calc.calculate_oee_components(shift_data)
        
        # Hedef karşılaştırma
        targets = {
            'oee': 85,
            'availability': 90,
            'performance': 95,
            'quality': 99.9
        }
        
        gaps = {
            'oee': targets['oee'] - oee_components['oee'],
            'availability': targets['availability'] - oee_components['availability'],
            'performance': targets['performance'] - oee_components['performance'],
            'quality': targets['quality'] - oee_components['quality']
        }
        
        # İyileştirme potansiyeli
        improvement_potential = self._calculate_oee_potential(oee_components, gaps)
        
        return {
            'current': oee_components,
            'daily_trend': daily_oee,
            'shift_comparison': shift_oee,
            'targets': targets,
            'gaps': gaps,
            'waterfall': waterfall,
            'improvement_potential': improvement_potential,
            'loss_analysis': {
                'availability_losses': {
                    'planned_downtime': 0,  # Veri yok
                    'unplanned_downtime': self.df['Durma_Suresi_Saat'].sum(),
                    'setup_time': self.df['KK_Hazirlik_Saat'].sum()
                },
                'performance_losses': {
                    'speed_loss': 0,  # Veri yok
                    'minor_stops': 0  # Veri yok
                },
                'quality_losses': {
                    'defects': self.df['Hatali'].sum(),
                    'rework': 0  # Veri yok
                }
            }
        }
    
    def get_live_monitoring_data(self):
        """
        Canlı izleme sayfası verileri (simülasyon)
        
        Returns:
            dict: Anlık üretim verileri
        """
        # Simüle edilmiş canlı veri
        current_time = datetime.now()
        
        # Son 20 motor
        recent_motors = self.df.tail(20)[['Motor_ID', 'Toplam_Uretim_Suresi', 
                                          'Verimlilik', 'Hatali']].copy()
        recent_motors['timestamp'] = [
            (current_time - timedelta(minutes=i*5)).strftime('%H:%M:%S')
            for i in range(19, -1, -1)
        ]
        
        # Anlık metrikler
        live_data = {
            'current_motor': 'BMC-1101',
            'status': 'Üretimde',
            'progress': 65,  # %
            'elapsed_time': 42.3,  # saat
            'estimated_completion': 65.0,  # saat
            'current_efficiency': 83.5
        }
        
        # Rastgele değerler ekle (simülasyon için)
        import random
        live_data['aktif_calisma'] = round(50 + random.random() * 10, 1)
        live_data['durma'] = round(random.random() * 3, 1)
        live_data['kk_hazirlik'] = round(3 + random.random() * 2, 1)
        live_data['kk_surec'] = round(5 + random.random() * 2, 1)
        
        # Anlık metrikler
        live_data['toplam_sure'] = sum([
            live_data['aktif_calisma'],
            live_data['durma'],
            live_data['kk_hazirlik'],
            live_data['kk_surec']
        ])
        
        live_data['verimlilik'] = round(
            (live_data['aktif_calisma'] / live_data['toplam_sure']) * 100, 1
        )
        
        # Kontrol limitleri kontrolü
        control_limits = self.stat_calc.calculate_control_limits(
            self.df['Toplam_Uretim_Suresi'].values
        )
        
        live_data['control_status'] = (
            'Normal' if control_limits['LCL'] <= live_data['toplam_sure'] <= control_limits['UCL']
            else 'Uyarı'
        )
        
        return {
            'live_metrics': live_data,
            'recent_production': recent_motors.to_dict('records'),
            'control_limits': control_limits,
            'current_shift': self._get_current_shift(),
            'shift_production': {
                'target': 12,
                'actual': len(recent_motors[recent_motors['timestamp'] > '08:00:00']),
                'efficiency': 82.5
            }
        }
    
    # Yardımcı fonksiyonlar
    def _generate_alerts(self):
        """Kritik uyarıları oluştur"""
        alerts = []
        
        # Verimlilik kontrolü
        if self.df['Verimlilik'].mean() < 85:
            alerts.append({
                'type': 'warning',
                'title': 'Düşük Verimlilik',
                'message': f"Ortalama verimlilik {self.df['Verimlilik'].mean():.1f}% - Hedef: 90%"
            })
        
        # Hata oranı kontrolü
        error_rate = self.df['Hatali'].mean() * 100
        if error_rate > 5:
            alerts.append({
                'type': 'danger',
                'title': 'Yüksek Hata Oranı',
                'message': f"Hata oranı %{error_rate:.1f} - Hedef: %2"
            })
        
        # Kontrol limiti ihlalleri
        control_violations = self.control_charts.check_western_electric_rules('Toplam_Uretim_Suresi')
        if any(len(v) > 0 for v in control_violations['violations'].values()):
            alerts.append({
                'type': 'danger',
                'title': 'Kontrol Limiti İhlali',
                'message': 'Süreç kontrol dışı - Western Electric kuralları ihlali'
            })
        
        # Yeterlilik uyarısı
        cap = self.capability.calculate_capability_indices('Toplam_Uretim_Suresi')
        if cap['indices']['Cpk'] < 1.0:
            alerts.append({
                'type': 'warning',
                'title': 'Düşük Süreç Yeterliliği',
                'message': f"Cpk = {cap['indices']['Cpk']} - Minimum: 1.33"
            })
        
        return alerts[:4]  # Maksimum 4 alert göster
    
    def _get_current_shift_status(self):
        """Mevcut vardiya durumu"""
        current_hour = datetime.now().hour
        
        if 8 <= current_hour < 16:
            shift = '08:00-16:00'
        elif 16 <= current_hour < 24:
            shift = '16:00-24:00'
        else:
            shift = '24:00-08:00'
        
        shift_data = self.df[self.df['Vardiya'] == shift]
        
        return {
            'shift': shift,
            'production_count': len(shift_data),
            'average_efficiency': round(shift_data['Verimlilik'].mean(), 1) if not shift_data.empty else 0,
            'defect_rate': round(shift_data['Hatali'].mean() * 100, 1) if not shift_data.empty else 0
        }
    
    def _interpret_control_charts(self, out_of_control):
        """Kontrol grafiği yorumlama"""
        interpretations = []
        
        if len(out_of_control.get('xbar', [])) > 0:
            interpretations.append("X-bar grafiğinde kontrol dışı noktalar tespit edildi - süreç ortalaması stabil değil")
        
        if len(out_of_control.get('ewma', [])) > 0:
            interpretations.append("EWMA grafiğinde trend tespit edildi - süreçte kayma var")
        
        if len(out_of_control.get('cusum', [])) > 0:
            interpretations.append("CUSUM grafiğinde sapma tespit edildi - küçük ama sürekli kayma")
        
        if not interpretations:
            interpretations.append("Tüm kontrol grafikleri normal sınırlar içinde")
        
        return {
            'status': 'Kontrol Altında' if not interpretations else 'Kontrol Dışı',
            'details': interpretations,
            'recommendation': 'Süreç stabil, mevcut performansı koruyun' if not interpretations 
                            else 'Süreç Kontrol Dışı - Acil Müdahale Gerekli'
        }
    
    def _generate_capability_recommendations(self, capability_data):
        """Yeterlilik önerileri"""
        recommendations = []
        cpk = capability_data['indices']['Cpk']
        
        if cpk < 0.67:
            recommendations.append({
                'priority': 'Kritik',
                'action': 'Süreç tamamen revize edilmeli',
                'expected_benefit': 'Hata oranında %50+ azalma'
            })
        elif cpk < 1.0:
            recommendations.append({
                'priority': 'Yüksek',
                'action': 'Süreç iyileştirme projesi başlatılmalı (DMAIC)',
                'expected_benefit': 'Cpk değerini 1.33 seviyesine çıkarma'
            })
        elif cpk < 1.33:
            recommendations.append({
                'priority': 'Orta',
                'action': 'Süreç optimizasyonu yapılmalı',
                'expected_benefit': '6-sigma seviyesine yaklaşma'
            })
        
        return recommendations
    
    def _prioritize_actions(self, pareto_report):
        """Aksiyonları önceliklendirme"""
        actions = []
        
        # En kritik hatalar için
        for defect in pareto_report.get('vital_few', {}).get('defects', [])[:2]:
            actions.append({
                'type': 'Hata Azaltma',
                'target': defect,
                'priority': 'P1',
                'timeframe': '1 hafta',
                'owner': 'Kalite Müdürlüğü'
            })
        
        # En büyük zaman kayıpları için
        for loss in pareto_report.get('vital_few', {}).get('time_losses', [])[:2]:
            actions.append({
                'type': 'Zaman Kaybı Azaltma',
                'target': loss,
                'priority': 'P2',
                'timeframe': '2 hafta',
                'owner': 'Üretim Müdürlüğü'
            })
        
        return sorted(actions, key=lambda x: x['priority'])
    
    def _calculate_oee_potential(self, current, gaps):
        """OEE iyileştirme potansiyeli"""
        return {
            'availability_potential': round(gaps['availability'] * 0.6, 1),  # %60 iyileştirme mümkün
            'performance_potential': round(gaps['performance'] * 0.4, 1),   # %40 iyileştirme mümkün
            'quality_potential': round(gaps['quality'] * 0.8, 1),          # %80 iyileştirme mümkün
            'total_oee_potential': round(
                (current['oee'] + min(gaps['oee'], 10)), 1  # Maksimum 10 puan iyileştirme
            ),
            'estimated_roi': {
                'investment': '500,000 TL',
                'annual_saving': '1,200,000 TL',
                'payback_months': 5
            }
        }
    
    def _get_current_shift(self):
        """Mevcut vardiyayı belirle"""
        hour = datetime.now().hour
        if 8 <= hour < 16:
            return '08:00-16:00'
        elif 16 <= hour < 24:
            return '16:00-24:00'
        else:
            return '24:00-08:00'
    
    def _sanitize_for_json(self, obj):
        """
        JSON serialization için veriyi temizle
        - Tuple key'leri string'e çevir
        - NaN ve Inf değerleri None yap
        - Pandas objelerini Python objelerine çevir
        """
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                # Tuple key'leri string'e çevir
                if isinstance(k, tuple):
                    new_key = "_".join(str(x) for x in k)
                else:
                    new_key = str(k)
                # Değeri recursive temizle
                new_dict[new_key] = self._sanitize_for_json(v)
            return new_dict
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, pd.DataFrame):
            # DataFrame'i dict'e çevir (orient='records' kullan)
            return obj.to_dict(orient='records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif pd.isna(obj):
            return None
        elif isinstance(obj, (np.int64, np.int32, np.int16)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    def export_dashboard_json(self, output_path='app/dashboard_data.json'):
        """
        Tüm dashboard verilerini JSON olarak export et
        
        Args:
            output_path: JSON dosya yolu
        """
        dashboard_data = {
            'overview': self.get_overview_data(),
            'control_charts': self.get_control_charts_data(),
            'capability': self.get_capability_data(),
            'pareto': self.get_pareto_data(),
            'oee': self.get_oee_data(),
            'live_monitoring': self.get_live_monitoring_data(),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'data_source': self.data_path,
                'total_records': len(self.df),
                'date_range': f"{self.df['Tarih'].min()} - {self.df['Tarih'].max()}"
            }
        }
        
        # JSON için veriyi temizle (tuple key'leri düzelt)
        clean_data = self._sanitize_for_json(dashboard_data)
        
        # JSON olarak kaydet
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ Dashboard verileri kaydedildi: {output_path}")
            return clean_data
        except Exception as e:
            print(f"❌ JSON kaydetme hatası: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


# TEST KODU
if __name__ == "__main__":
    print("=== ANA DASHBOARD ===\n")
    
    dashboard = Dashboard()
    
    # 1. Genel bakış
    print("1. Genel Bakış:")
    overview = dashboard.get_overview_data()
    print(f"   KPI Sayısı: {len(overview['kpis'])}")
    print(f"   Alert Sayısı: {len(overview['alerts'])}")
    
    # 2. Kontrol grafikleri
    print("\n2. Kontrol Grafikleri:")
    control = dashboard.get_control_charts_data()
    print(f"   Durum: {control['interpretation']['recommendation']}")
    
    # 3. Yeterlilik
    print("\n3. Süreç Yeterliliği:")
    capability = dashboard.get_capability_data()
    print(f"   Ana Cpk: {capability['main_capability']['indices']['Cpk']}")
    print(f"   Sigma Seviyesi: {capability['main_capability']['sigma_level']}")
    
    # 4. JSON Export
    print("\n4. JSON Export:")
    dashboard.export_dashboard_json()