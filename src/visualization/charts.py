"""
Grafik Fonksiyonları Modülü
Dashboard için tüm grafik verilerini hazırlar
"""

import pandas as pd
import numpy as np
from scipy import stats  # BU SATIR EKLENDİ
import sys
import os
from datetime import datetime, timedelta

# Path ayarlaması
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.data_loader import DataLoader
from src.utils.statistics import StatisticalCalculator
from src.utils.constants import TARGETS, SPEC_LIMITS

class ChartGenerator:
    """
    Dashboard için grafik verilerini hazırlayan sınıf
    HTML/JavaScript tarafında kullanılmak üzere JSON formatında veri döndürür
    """
    
    def __init__(self, data_path='data/raw/DATA_SET_MOTOR.xlsx'):
        """
        Args:
            data_path: Excel veri dosyası yolu
        """
        self.loader = DataLoader(data_path)
        self.df = self.loader.load_data()
        self.stat_calc = StatisticalCalculator()
        
    def get_kpi_cards(self):
        """
        Dashboard üst kısmındaki KPI kartları için veri
        
        Returns:
            dict: KPI verileri (değer, trend, hedef, renk)
        """
        stats = self.loader.get_summary_stats()
        
        # Son 7 gün için trend hesapla
        recent_data = self.df.tail(30)
        older_data = self.df.iloc[-60:-30] if len(self.df) > 60 else self.df.head(30)
        
        kpis = {
            'oee': {
                'title': 'OEE',
                'value': stats['oee'],
                'unit': '%',
                'target': TARGETS['OEE'],
                'trend': round(stats['oee'] - 75, 1),  # Önceki değerden fark
                'color': 'warning' if stats['oee'] < TARGETS['OEE'] else 'success',
                'icon': 'fa-gauge-high'
            },
            'efficiency': {
                'title': 'Verimlilik',
                'value': stats['ortalama_verimlilik'],
                'unit': '%',
                'target': TARGETS['Verimlilik'],
                'trend': round(recent_data['Verimlilik'].mean() - older_data['Verimlilik'].mean(), 1),
                'color': 'success' if stats['ortalama_verimlilik'] >= TARGETS['Verimlilik'] else 'warning',
                'icon': 'fa-chart-line'
            },
            'quality': {
                'title': 'Kalite',
                'value': stats['kalite_orani'],
                'unit': '%',
                'target': TARGETS['Kalite'],
                'trend': round(stats['kalite_orani'] - 95, 1),
                'color': 'danger' if stats['kalite_orani'] < 95 else 'success',
                'icon': 'fa-check-circle'
            },
            'production': {
                'title': 'Üretim',
                'value': stats['toplam_motor'],
                'unit': 'adet',
                'target': 100,
                'trend': 0,
                'color': 'info',
                'icon': 'fa-industry'
            }
        }
        
        return kpis
    
    def get_time_series_chart(self):
        """
        Zaman serisi grafiği için veri (Plotly.js formatında)
        
        Returns:
            dict: Plotly trace'leri ve layout
        """
        # Günlük aggregasyon
        daily_data = self.loader.get_time_series_data()
        
        # 3 günlük hareketli ortalama
        daily_data['MA_3'] = daily_data['Verimlilik'].rolling(window=3, center=True).mean()
        
        traces = [
            {
                'x': daily_data['Tarih'].dt.strftime('%Y-%m-%d').tolist(),
                'y': daily_data['Verimlilik'].round(2).tolist(),
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Günlük Verimlilik',
                'line': {'color': '#2563eb', 'width': 2},
                'marker': {'size': 6}
            },
            {
                'x': daily_data['Tarih'].dt.strftime('%Y-%m-%d').tolist(),
                'y': daily_data['MA_3'].round(2).tolist(),
                'type': 'scatter',
                'mode': 'lines',
                'name': '3-Gün MA',
                'line': {'color': '#ef4444', 'width': 2, 'dash': 'dash'}
            },
            {
                'x': daily_data['Tarih'].dt.strftime('%Y-%m-%d').tolist(),
                'y': [TARGETS['Verimlilik']] * len(daily_data),
                'type': 'scatter',
                'mode': 'lines',
                'name': 'Hedef',
                'line': {'color': '#10b981', 'width': 1, 'dash': 'dot'}
            }
        ]
        
        layout = {
            'title': 'Verimlilik Trendi',
            'xaxis': {'title': 'Tarih'},
            'yaxis': {'title': 'Verimlilik (%)'},
            'height': 350,
            'hovermode': 'x unified'
        }
        
        return {
            'traces': traces,
            'layout': layout
        }
    
    def get_control_chart_data(self, variable='Toplam_Uretim_Suresi', chart_type='shewhart'):
        """
        Kontrol grafikleri için veri (Shewhart, EWMA, CUSUM)
        
        Args:
            variable: İzlenecek değişken
            chart_type: 'shewhart', 'ewma', 'cusum'
            
        Returns:
            dict: Plotly formatında grafik verisi
        """
        data = self.df[variable].values
        
        if chart_type == 'shewhart':
            # Shewhart X-bar kontrol grafiği
            limits = self.stat_calc.calculate_control_limits(data, 'xbar')
            
            trace = {
                'x': list(range(1, len(data) + 1)),
                'y': data.tolist(),
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Gözlem',
                'marker': {
                    'color': ['red' if (d > limits['UCL'] or d < limits['LCL']) else 'blue' 
                             for d in data],
                    'size': 6
                }
            }
            
            # Kontrol limitleri
            ucl_trace = {
                'x': list(range(1, len(data) + 1)),
                'y': [limits['UCL']] * len(data),
                'type': 'scatter',
                'mode': 'lines',
                'name': f"UCL ({limits['UCL']})",
                'line': {'color': 'red', 'dash': 'dash'}
            }
            
            cl_trace = {
                'x': list(range(1, len(data) + 1)),
                'y': [limits['CL']] * len(data),
                'type': 'scatter',
                'mode': 'lines',
                'name': f"CL ({limits['CL']})",
                'line': {'color': 'green', 'dash': 'solid'}
            }
            
            lcl_trace = {
                'x': list(range(1, len(data) + 1)),
                'y': [limits['LCL']] * len(data),
                'type': 'scatter',
                'mode': 'lines',
                'name': f"LCL ({limits['LCL']})",
                'line': {'color': 'red', 'dash': 'dash'}
            }
            
            return {
                'traces': [trace, ucl_trace, cl_trace, lcl_trace],
                'layout': {
                    'title': f'Shewhart Kontrol Grafiği - {variable}',
                    'xaxis': {'title': 'Gözlem No'},
                    'yaxis': {'title': variable},
                    'height': 400
                },
                'limits': limits
            }
            
        elif chart_type == 'ewma':
            # EWMA grafiği
            ewma_result = self.stat_calc.calculate_ewma(data)
            
            trace = {
                'x': list(range(1, len(data) + 1)),
                'y': ewma_result['ewma_values'],
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'EWMA',
                'line': {'color': '#2563eb', 'width': 2}
            }
            
            ucl_trace = {
                'x': list(range(1, len(data) + 1)),
                'y': ewma_result['UCL'],
                'type': 'scatter',
                'mode': 'lines',
                'name': 'UCL',
                'line': {'color': 'red', 'dash': 'dash'}
            }
            
            lcl_trace = {
                'x': list(range(1, len(data) + 1)),
                'y': ewma_result['LCL'],
                'type': 'scatter',
                'mode': 'lines',
                'name': 'LCL',
                'line': {'color': 'red', 'dash': 'dash'}
            }
            
            return {
                'traces': [trace, ucl_trace, lcl_trace],
                'layout': {
                    'title': f'EWMA Kontrol Grafiği - {variable}',
                    'xaxis': {'title': 'Gözlem No'},
                    'yaxis': {'title': 'EWMA Değeri'},
                    'height': 400
                }
            }
            
        elif chart_type == 'cusum':
            # CUSUM grafiği
            cusum_result = self.stat_calc.calculate_cusum(data)
            
            trace_plus = {
                'x': list(range(1, len(data) + 1)),
                'y': cusum_result['C_plus'],
                'type': 'scatter',
                'mode': 'lines',
                'name': 'C+',
                'line': {'color': '#2563eb', 'width': 2}
            }
            
            trace_minus = {
                'x': list(range(1, len(data) + 1)),
                'y': cusum_result['C_minus'],
                'type': 'scatter',
                'mode': 'lines',
                'name': 'C-',
                'line': {'color': '#ef4444', 'width': 2}
            }
            
            h_limit = {
                'x': list(range(1, len(data) + 1)),
                'y': [cusum_result['h_limit']] * len(data),
                'type': 'scatter',
                'mode': 'lines',
                'name': f"H = {cusum_result['h_limit']}",
                'line': {'color': 'green', 'dash': 'dash'}
            }
            
            return {
                'traces': [trace_plus, trace_minus, h_limit],
                'layout': {
                    'title': f'CUSUM Kontrol Grafiği - {variable}',
                    'xaxis': {'title': 'Gözlem No'},
                    'yaxis': {'title': 'CUSUM Değeri'},
                    'height': 400
                },
                'out_of_control': cusum_result['out_of_control_points']
            }
    
    def get_pareto_chart_data(self):
        """
        Pareto grafiği için veri (Chart.js formatında)
        
        Returns:
            dict: Bar + Line kombinasyonu için veri
        """
        pareto = self.loader.get_pareto_data()
        
        if pareto.empty:
            return None
            
        return {
            'labels': pareto['Hata_Nedeni'].tolist(),
            'datasets': [
                {
                    'type': 'bar',
                    'label': 'Hata Sayısı',
                    'data': pareto['Adet'].tolist(),
                    'backgroundColor': '#2563eb',
                    'borderColor': '#1d4ed8',
                    'borderWidth': 1,
                    'yAxisID': 'y'
                },
                {
                    'type': 'line',
                    'label': 'Kümülatif %',
                    'data': pareto['Kumulatif_Yuzde'].round(1).tolist(),
                    'borderColor': '#ef4444',
                    'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                    'borderWidth': 2,
                    'fill': True,
                    'yAxisID': 'y1'
                }
            ]
        }
    
    def get_histogram_capability_data(self):
        """
        Süreç yeterlilik histogramı için veri
        
        Returns:
            dict: Histogram ve normal dağılım eğrisi
        """
        variable = 'Toplam_Uretim_Suresi'
        data = self.df[variable].values
        
        # Histogram hesapla
        hist, bin_edges = np.histogram(data, bins=20)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Normal dağılım eğrisi
        mean = np.mean(data)
        sigma = np.std(data, ddof=1)
        x_norm = np.linspace(data.min() - 5, data.max() + 5, 100)
        y_norm = stats.norm.pdf(x_norm, mean, sigma) * len(data) * (bin_edges[1] - bin_edges[0])
        
        # Spec limitleri
        spec = SPEC_LIMITS.get(variable, {})
        
        return {
            'histogram': {
                'x': bin_centers.tolist(),
                'y': hist.tolist(),
                'type': 'bar',
                'name': 'Dağılım',
                'marker': {'color': '#2563eb'}
            },
            'normal_curve': {
                'x': x_norm.tolist(),
                'y': y_norm.tolist(),
                'type': 'scatter',
                'mode': 'lines',
                'name': 'Normal Dağılım',
                'line': {'color': '#10b981', 'width': 2}
            },
            'spec_limits': {
                'USL': spec.get('USL', mean + 3*sigma),
                'LSL': spec.get('LSL', mean - 3*sigma),
                'Target': spec.get('Target', mean)
            },
            'statistics': {
                'mean': round(mean, 2),
                'std': round(sigma, 3),
                'min': round(data.min(), 2),
                'max': round(data.max(), 2)
            }
        }
    
    def get_oee_waterfall_chart(self):
        """
        OEE kayıpları için waterfall grafiği
        
        Returns:
            dict: Plotly waterfall chart verisi
        """
        stats = self.loader.get_summary_stats()
        
        # OEE bileşenleri
        availability = stats['ort_kullanilabilirlik']
        performance = 100  # Varsayılan
        quality = stats['kalite_orani']
        
        # Kayıplar
        availability_loss = 100 - availability
        performance_loss = 0  # Veri yok
        quality_loss = 100 - quality
        
        return {
            'x': ['Teorik Max', 'Durma Kaybı', 'Performans Kaybı', 'Kalite Kaybı', 'OEE'],
            'y': [100, -availability_loss, -performance_loss, -quality_loss, None],
            'text': ['100%', f'-{availability_loss:.1f}%', f'-{performance_loss:.1f}%', 
                    f'-{quality_loss:.1f}%', f'{stats["oee"]:.1f}%'],
            'type': 'waterfall',
            'orientation': 'v',
            'measure': ['relative', 'relative', 'relative', 'relative', 'total'],
            'increasing': {'marker': {'color': '#10b981'}},
            'decreasing': {'marker': {'color': '#ef4444'}},
            'totals': {'marker': {'color': '#2563eb'}}
        }
    
    def get_shift_comparison_chart(self):
        """
        Vardiya karşılaştırma radar grafiği
        
        Returns:
            dict: Chart.js radar chart verisi
        """
        shift_perf = self.loader.get_vardiya_performance()
        
        # Her vardiya için metrikler
        shifts = []
        for shift in shift_perf.index:
            shift_data = shift_perf.loc[shift]
            shifts.append({
                'label': shift,
                'data': [
                    shift_data[('Verimlilik', 'mean')],
                    100 - shift_data[('Hatali', '<lambda_0>')],  # Kalite
                    100 - (shift_data[('Durma_Suresi_Saat', 'mean')] / 
                          shift_data[('Toplam_Uretim_Suresi', 'mean')]) * 100,  # Kullanılabilirlik
                    shift_data[('Aktif_Calisma_Saat', 'mean')] / 
                    shift_data[('Toplam_Uretim_Suresi', 'mean')] * 100,  # Performans
                    shift_data[('Motor_ID', 'count')]  # Üretim adedi (normalize)
                ]
            })
        
        colors = ['#2563eb', '#10b981', '#f59e0b']
        
        return {
            'labels': ['Verimlilik', 'Kalite', 'Kullanılabilirlik', 'Performans', 'Üretim'],
            'datasets': [
                {
                    'label': shifts[i]['label'],
                    'data': [round(d, 1) for d in shifts[i]['data']],
                    'borderColor': colors[i],
                    'backgroundColor': colors[i] + '33',  # Transparency
                    'borderWidth': 2,
                    'pointRadius': 4
                }
                for i in range(len(shifts))
            ]
        }
    
    def get_heatmap_data(self):
        """
        Gün-Vardiya verimlilik ısı haritası
        
        Returns:
            dict: Plotly heatmap verisi
        """
        # Pivot table oluştur
        heatmap_data = self.df.pivot_table(
            values='Verimlilik',
            index='Vardiya',
            columns=self.df['Tarih'].dt.date,
            aggfunc='mean'
        )
        
        # Tarih formatı düzelt
        column_labels = [str(col) for col in heatmap_data.columns]
        
        return {
            'z': heatmap_data.values.tolist(),
            'x': column_labels,
            'y': heatmap_data.index.tolist(),
            'type': 'heatmap',
            'colorscale': 'RdYlGn',
            'colorbar': {'title': 'Verimlilik (%)'},
            'hovertemplate': 'Tarih: %{x}<br>Vardiya: %{y}<br>Verimlilik: %{z:.1f}%<extra></extra>'
        }
    
    def get_all_charts_config(self):
        """
        Tüm grafikleri tek bir config objesi olarak döndür
        HTML/JS tarafında kullanmak için
        
        Returns:
            dict: Tüm grafik konfigürasyonları
        """
        return {
            'kpi_cards': self.get_kpi_cards(),
            'time_series': self.get_time_series_chart(),
            'control_charts': {
                'shewhart': self.get_control_chart_data('Toplam_Uretim_Suresi', 'shewhart'),
                'ewma': self.get_control_chart_data('Toplam_Uretim_Suresi', 'ewma'),
                'cusum': self.get_control_chart_data('Toplam_Uretim_Suresi', 'cusum')
            },
            'pareto': self.get_pareto_chart_data(),
            'capability': self.get_histogram_capability_data(),
            'oee_waterfall': self.get_oee_waterfall_chart(),
            'shift_comparison': self.get_shift_comparison_chart(),
            'heatmap': self.get_heatmap_data(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# TEST KODU
if __name__ == "__main__":
    print("=== DASHBOARD GRAFİK VERİLERİ ===\n")
    
    chart_gen = ChartGenerator()
    
    # KPI Kartları
    print("1. KPI Kartları:")
    kpis = chart_gen.get_kpi_cards()
    for key, kpi in kpis.items():
        print(f"   {kpi['title']}: {kpi['value']}{kpi['unit']} (Hedef: {kpi['target']})")
    
    # Pareto
    print("\n2. Pareto Verisi:")
    pareto = chart_gen.get_pareto_chart_data()
    if pareto:
        print(f"   En çok hata: {pareto['labels'][0]} ({pareto['datasets'][0]['data'][0]} adet)")
    
    # Kontrol Limitleri
    print("\n3. Kontrol Limitleri:")
    control = chart_gen.get_control_chart_data()
    print(f"   UCL: {control['limits']['UCL']}")
    print(f"   CL: {control['limits']['CL']}")
    print(f"   LCL: {control['limits']['LCL']}")