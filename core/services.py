# core/services.py
from core.schemas import validar_excel_estructura
from core.engine import ejecutar_motor_colab
import pandas as pd

class PlanificacionService:
    @staticmethod
    def procesar_pipeline_industrial(excel_file):
        # 1. Validar formato
        validar_excel_estructura(excel_file)
        
        # 2. Correr el potente algoritmo multinivel del Colab
        df_plan = ejecutar_motor_colab(excel_file)
        
        # 3. Generar métricas y KPIs rápidos para Streamlit
        # (Libras asignadas, capacidad utilizada por día, setups generados)
        return df_plan
