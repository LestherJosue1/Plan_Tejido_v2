import pandas as pd
from typing import Tuple
from core.schemas import DataValidator
from core.engine import ProductionEngine
from core.exceptions import ConfigurationError

class PlanningOrchestratorService:
    """Capa de servicio encargada de coordinar la ingesta, ejecución de lógica y cálculo de KPIs."""

    @staticmethod
    def ejecutar_pipeline_industrial(
        df_estado: pd.DataFrame, df_demanda: pd.DataFrame, df_params: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Orquesta de punta a punta la generación del plan de planta."""
        
        # 1. Validación de Calidad de Datos
        estado, demanda, params = DataValidator.validate_and_clean(df_estado, df_demanda, df_params)

        # 2. Extracción segura de parámetros operativos
        try:
            f_ini = pd.to_datetime(params.loc[params["Campo"] == "Fecha_inicio_plan", "Valor"].values[0]).normalize()
            f_fin = pd.to_datetime(params.loc[params["Campo"] == "Fecha_fin_plan", "Valor"].values[0]).normalize()
            fechas = pd.date_range(f_ini, f_fin)
        except Exception:
            raise ConfigurationError("Las fechas límites del plan ('Fecha_inicio_plan', 'Fecha_fin_plan') faltan o tienen formatos erróneos.")

        capacidad_val = params.loc[params["Campo"] == "Capacidad_estandar_lbs", "Valor"]
        capacidad_estandar = float(capacidad_val.values[0]) if not capacidad_val.empty else 500.0

        # 3. Ejecución del Core del Motor Analítico
        maquinas_disponibles = estado["MAQUINA"].unique().tolist()
        plan_base = ProductionEngine.build_plan_base(estado, fechas)
        asignaciones = ProductionEngine.generar_asignacion_optima(demanda, fechas, maquinas_disponibles, capacidad_estandar)
        plan_final = ProductionEngine.integrar_y_clasificar_plan(plan_base, asignaciones)

        # 4. Agregación Vectorial de KPIs del Negocio
        maquinas_dia = plan_final.groupby("FECHA")["ACTIVA_DIA"].sum().reset_index(name="MAQS_ACTIVAS")
        setups_dia = plan_final.groupby("FECHA")["REQUIERE_SETUP"].sum().reset_index(name="SETUPS_REQUERIDOS")
        kpis_diarios = pd.merge(maquinas_dia, setups_dia, on="FECHA")

        # 5. Generación de la Matriz Pivotizada Cruzada Comercial estilo Excel
        pivot_lbs = plan_final.pivot_table(
            index="MAQUINA", columns="FECHA", values="PLAN_NUEVO_LBS", aggfunc="sum", fill_value=0.0
        )

        return plan_final, kpis_diarios, pivot_lbs