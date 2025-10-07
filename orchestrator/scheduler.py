"""Simple scheduler for MVP (alternative to Airflow)."""
import time
import schedule
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingesta.oficial import fetch_dge, fetch_inegi
from etl.normaliza import normalizar_dge
from analytics.kpis import recalcular_kpis
from analytics.alertas import evaluar_alertas


def job_ingesta_oficial():
    """Job to ingest official data."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] Iniciando job de ingesta oficial")
    print(f"{'='*60}")
    
    try:
        # Fetch data from sources
        fetch_dge()
        fetch_inegi()
        
        # Normalize data
        normalizar_dge()
        
        print(f"[{datetime.now()}] Job de ingesta completado exitosamente")
    except Exception as e:
        print(f"[ERROR] Job de ingesta falló: {e}")


def job_analytics():
    """Job to calculate KPIs and evaluate alerts."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] Iniciando job de analítica")
    print(f"{'='*60}")
    
    try:
        # Calculate KPIs
        recalcular_kpis()
        
        # Evaluate alerts
        evaluar_alertas()
        
        print(f"[{datetime.now()}] Job de analítica completado exitosamente")
    except Exception as e:
        print(f"[ERROR] Job de analítica falló: {e}")


def main():
    """Main scheduler loop."""
    print("="*60)
    print("Episcopio Scheduler - MVP")
    print("="*60)
    print(f"Iniciado en: {datetime.now()}")
    print(f"Zona horaria: America/Merida")
    print("="*60)
    
    # Schedule jobs
    # Ingesta oficial cada 6 horas
    schedule.every(6).hours.do(job_ingesta_oficial)
    
    # Analítica cada 1 hora
    schedule.every(1).hours.do(job_analytics)
    
    # Run immediately on startup
    print("\nEjecutando jobs iniciales...")
    job_ingesta_oficial()
    job_analytics()
    
    print("\n" + "="*60)
    print("Scheduler iniciado. Esperando próximos jobs...")
    print("Presiona Ctrl+C para detener")
    print("="*60 + "\n")
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nScheduler detenido por usuario")
        print(f"Finalizado en: {datetime.now()}")


if __name__ == "__main__":
    main()
