import pandas as pd
from typing import Tuple
from core.schemas import DataValidator
from core.engine import ProductionEngineColab

class PlanningOrchestratorService:
    """Orquestador maestro para el procesamiento de simulación textil multinivel."""

    @staticmethod
    def ejecutar_pipeline_industrial(excel_file) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        # 1. Ingesta y validación estricta de las 8 pestañas
        dfs = DataValidator.validate_and_load(excel_file)
        
        # 2. Correr motor analítico estructurado de Colab
        df_plan = ProductionEngineColab.ejecutar_planificacion(dfs)
        
        # 3. Generación vectorial de KPIs para los dashboards
        df_plan["ACTIVA_DIA"] = np.where(df_plan["PLAN_NUEVO_LBS"] > 0, 1, 0)
        
        kpis_diarios = df_plan.groupby("FECHA").agg(
            MAQS_ACTIVAS=("ACTIVA_DIA", "sum"),
            LBS_TOTALES=("PLAN_NUEVO_LBS", "sum")
        ).reset_index()
        
        # 4. Matriz Pivotizada Comercial Cruzada (Estilo Excel)
        pivot_lbs = df_plan.pivot_table(
            index="MAQUINA", 
            columns="FECHA", 
            values="PLAN_NUEVO_LBS", 
            aggfunc="sum", 
            fill_value=0.0
        )
        
        return df_plan, kpis_diarios, pivot_lbs
