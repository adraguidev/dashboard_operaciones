import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any
import logging
from fpdf import FPDF
import seaborn as sns

class ReportGenerator:
    def __init__(self, system_monitor):
        self.system_monitor = system_monitor
        self.reports_path = "reports"
        
        if not os.path.exists(self.reports_path):
            os.makedirs(self.reports_path)
    
    def generate_performance_report(self, days: int = 7, format: str = "PDF") -> str:
        """Genera un reporte de rendimiento del sistema."""
        try:
            # Recopilar datos históricos
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Obtener métricas del sistema
            metrics = list(self.system_monitor.db.system_metrics.find({
                "timestamp": {"$gte": start_date, "$lte": end_date}
            }).sort("timestamp", 1))
            
            if not metrics:
                return ""
            
            # Crear DataFrame
            df = pd.DataFrame(metrics)
            
            # Generar gráficos
            plt.figure(figsize=(12, 8))
            
            # CPU Usage
            plt.subplot(3, 1, 1)
            plt.plot(df['timestamp'], df['cpu_usage'], 'b-')
            plt.title('CPU Usage Over Time')
            plt.ylabel('CPU %')
            plt.grid(True)
            
            # Memory Usage
            plt.subplot(3, 1, 2)
            plt.plot(df['timestamp'], df['memory_percent'], 'r-')
            plt.title('Memory Usage Over Time')
            plt.ylabel('Memory %')
            plt.grid(True)
            
            # Disk Usage
            plt.subplot(3, 1, 3)
            plt.plot(df['timestamp'], df['disk_percent'], 'g-')
            plt.title('Disk Usage Over Time')
            plt.ylabel('Disk %')
            plt.grid(True)
            
            plt.tight_layout()
            
            # Guardar reporte según formato
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format.upper() == "PDF":
                report_file = os.path.join(self.reports_path, f"performance_report_{timestamp}.pdf")
                pdf = FPDF()
                pdf.add_page()
                
                # Título
                pdf.set_font('Arial', 'B', 16)
                pdf.cell(0, 10, 'System Performance Report', 0, 1, 'C')
                pdf.ln(10)
                
                # Información general
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 10, f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', 0, 1)
                pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
                pdf.ln(10)
                
                # Guardar gráfico
                plt.savefig('temp_plot.png')
                pdf.image('temp_plot.png', x=10, w=190)
                os.remove('temp_plot.png')
                
                # Estadísticas
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Statistics', 0, 1)
                pdf.ln(5)
                
                stats = {
                    'CPU Usage (avg)': f"{df['cpu_usage'].mean():.1f}%",
                    'CPU Usage (max)': f"{df['cpu_usage'].max():.1f}%",
                    'Memory Usage (avg)': f"{df['memory_percent'].mean():.1f}%",
                    'Memory Usage (max)': f"{df['memory_percent'].max():.1f}%",
                    'Disk Usage (current)': f"{df['disk_percent'].iloc[-1]:.1f}%"
                }
                
                pdf.set_font('Arial', '', 12)
                for key, value in stats.items():
                    pdf.cell(0, 10, f'{key}: {value}', 0, 1)
                
                pdf.output(report_file)
                
            elif format.upper() == "EXCEL":
                report_file = os.path.join(self.reports_path, f"performance_report_{timestamp}.xlsx")
                with pd.ExcelWriter(report_file) as writer:
                    df.to_excel(writer, sheet_name='Raw Data', index=False)
                    
                    # Crear hoja de resumen
                    summary = pd.DataFrame({
                        'Metric': ['CPU Usage (avg)', 'CPU Usage (max)', 'Memory Usage (avg)',
                                'Memory Usage (max)', 'Disk Usage (current)'],
                        'Value': [
                            f"{df['cpu_usage'].mean():.1f}%",
                            f"{df['cpu_usage'].max():.1f}%",
                            f"{df['memory_percent'].mean():.1f}%",
                            f"{df['memory_percent'].max():.1f}%",
                            f"{df['disk_percent'].iloc[-1]:.1f}%"
                        ]
                    })
                    summary.to_excel(writer, sheet_name='Summary', index=False)
            
            else:  # CSV
                report_file = os.path.join(self.reports_path, f"performance_report_{timestamp}.csv")
                df.to_csv(report_file, index=False)
            
            plt.close()
            return report_file
            
        except Exception as e:
            logging.error(f"Error al generar reporte de rendimiento: {str(e)}")
            return ""
    
    def generate_error_report(self, days: int = 7, format: str = "PDF") -> str:
        """Genera un reporte de errores y advertencias."""
        try:
            # Recopilar logs
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logs = self.system_monitor.get_system_logs(
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            if not logs:
                return ""
            
            df = pd.DataFrame(logs)
            
            # Generar reporte según formato
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.upper() == "PDF":
                report_file = os.path.join(self.reports_path, f"error_report_{timestamp}.pdf")
                pdf = FPDF()
                pdf.add_page()
                
                # Título
                pdf.set_font('Arial', 'B', 16)
                pdf.cell(0, 10, 'System Error Report', 0, 1, 'C')
                pdf.ln(10)
                
                # Información general
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 10, f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', 0, 1)
                pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
                pdf.ln(10)
                
                # Resumen por nivel
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Summary by Level', 0, 1)
                pdf.ln(5)
                
                level_counts = df['level'].value_counts()
                pdf.set_font('Arial', '', 12)
                for level, count in level_counts.items():
                    pdf.cell(0, 10, f'{level}: {count} occurrences', 0, 1)
                
                # Últimos errores
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Latest Errors', 0, 1)
                pdf.ln(5)
                
                pdf.set_font('Arial', '', 10)
                for _, row in df[df['level'] == 'ERROR'].head(10).iterrows():
                    pdf.multi_cell(0, 10, f"{row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {row['message']}")
                    pdf.ln(5)
                
                pdf.output(report_file)
                
            elif format.upper() == "EXCEL":
                report_file = os.path.join(self.reports_path, f"error_report_{timestamp}.xlsx")
                with pd.ExcelWriter(report_file) as writer:
                    df.to_excel(writer, sheet_name='All Logs', index=False)
                    
                    # Hoja de resumen
                    summary = pd.DataFrame({
                        'Level': level_counts.index,
                        'Count': level_counts.values
                    })
                    summary.to_excel(writer, sheet_name='Summary', index=False)
                    
            else:  # CSV
                report_file = os.path.join(self.reports_path, f"error_report_{timestamp}.csv")
                df.to_csv(report_file, index=False)
            
            return report_file
            
        except Exception as e:
            logging.error(f"Error al generar reporte de errores: {str(e)}")
            return ""
    
    def generate_usage_report(self, days: int = 30, format: str = "PDF") -> str:
        """Genera un reporte de uso del sistema por módulo."""
        try:
            # Recopilar estadísticas de uso
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            usage_stats = list(self.system_monitor.db.module_usage.find({
                "timestamp": {"$gte": start_date, "$lte": end_date}
            }).sort("timestamp", 1))
            
            if not usage_stats:
                return ""
            
            df = pd.DataFrame(usage_stats)
            
            # Generar reporte según formato
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.upper() == "PDF":
                report_file = os.path.join(self.reports_path, f"usage_report_{timestamp}.pdf")
                pdf = FPDF()
                pdf.add_page()
                
                # Título
                pdf.set_font('Arial', 'B', 16)
                pdf.cell(0, 10, 'System Usage Report', 0, 1, 'C')
                pdf.ln(10)
                
                # Información general
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 10, f'Period: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}', 0, 1)
                pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
                pdf.ln(10)
                
                # Uso por módulo
                module_usage = df.groupby('module')['access_count'].sum()
                
                plt.figure(figsize=(10, 6))
                plt.pie(module_usage.values, labels=module_usage.index, autopct='%1.1f%%')
                plt.title('Module Usage Distribution')
                plt.savefig('temp_plot.png')
                pdf.image('temp_plot.png', x=10, w=190)
                os.remove('temp_plot.png')
                plt.close()
                
                # Estadísticas detalladas
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Detailed Statistics', 0, 1)
                pdf.ln(5)
                
                pdf.set_font('Arial', '', 12)
                for module, count in module_usage.items():
                    pdf.cell(0, 10, f'{module}: {count} accesses', 0, 1)
                
                pdf.output(report_file)
                
            elif format.upper() == "EXCEL":
                report_file = os.path.join(self.reports_path, f"usage_report_{timestamp}.xlsx")
                with pd.ExcelWriter(report_file) as writer:
                    df.to_excel(writer, sheet_name='Raw Data', index=False)
                    
                    # Hoja de resumen
                    summary = pd.DataFrame({
                        'Module': module_usage.index,
                        'Access Count': module_usage.values
                    })
                    summary.to_excel(writer, sheet_name='Summary', index=False)
                    
            else:  # CSV
                report_file = os.path.join(self.reports_path, f"usage_report_{timestamp}.csv")
                df.to_csv(report_file, index=False)
            
            return report_file
            
        except Exception as e:
            logging.error(f"Error al generar reporte de uso: {str(e)}")
            return ""