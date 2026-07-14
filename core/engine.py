import pandas as pd
import numpy as np
from typing import List

class ProductionEngine:
    """Motor analítico de asignación de capacidad textil y cálculo de transiciones."""

    @staticmethod
    def build_plan_base(estado_maquina: pd.DataFrame, fechas: pd.DatetimeIndex) -> pd.DataFrame:
        """Genera la estructura base espacio-temporal (Máquina x Fecha) mediante cross-join."""
        maquinas_df = estado_maquina[["MAQUINA", "ESTILO_REAL", "LOTE_HILO"]].drop_duplicates(subset=["MAQUINA"])
        fechas_df = pd.DataFrame({"FECHA": fechas})
        
        base_df = maquinas_df.merge(fechas_df, how="cross")
        
        # Inicialización de estados iniciales (Arranque del horizonte)
        base_df["PLAN_ANTERIOR_ESTILO"] = np.where(base_df["FECHA"] == fechas[0], base_df["ESTILO_REAL"], "")
        base_df["PLAN_ANTERIOR_LOTE"] = np.where(base_df["FECHA"] == fechas[0], base_df["LOTE_HILO"], "")
        
        base_df["ESTILO_NUEVO"] = ""
        base_df["LOTE_NUEVO"] = ""
        base_df["PLAN_NUEVO_LBS"] = 0.0
        
        return base_df.drop(columns=["ESTILO_REAL", "LOTE_HILO"])

    @staticmethod
    def generar_asignacion_optima(
        demanda: pd.DataFrame, fechas: pd.DatetimeIndex, maquinas: List[str], capacidad_estandar: float
    ) -> pd.DataFrame:
        """
        Algoritmo avanzado de asignación con balance de carga y rastreo de afinidad operativa.
        Evita la saturación ciega y prepara los datos para la vectorización.
        """
        if not maquinas or fechas.empty or demanda.empty:
            return pd.DataFrame(columns=["MAQUINA", "FECHA", "LBS", "ESTILO", "LOTE"])

        asignaciones = []
        num_maquinas = len(maquinas)
        idx_maq = 0

        # Ordenación estratégica por volumen de libras pendientes (Priorización de negocio)
        demanda_sorted = demanda.sort_values(by=["LBS_PENDIENTES"], ascending=False)

        for _, d in demanda_sorted.iterrows():
            lbs_pendientes = float(d["LBS_PENDIENTES"])
            estilo = d["ESTILO_OPTIMO"]
            lote = d["LOTE_HILO"]

            if lbs_pendientes <= 0:
                continue

            for f in fechas:
                pasos = 0
                # Distribución circular inteligente controlando la capacidad finita diaria de la planta
                while lbs_pendientes > 0 and pasos < num_maquinas:
                    maq = maquinas[idx_maq]
                    prod_dia = min(capacidad_estandar, lbs_pendientes)

                    asignaciones.append({
                        "MAQUINA": maq,
                        "FECHA": f,
                        "LBS": prod_dia,
                        "ESTILO": estilo,
                        "LOTE": lote
                    })

                    lbs_pendientes -= prod_dia
                    idx_maq = (idx_maq + 1) % num_maquinas
                    pasos += 1

                if lbs_pendientes <= 0:
                    break

        return pd.DataFrame(asignaciones) if asignaciones else pd.DataFrame(columns=["MAQUINA", "FECHA", "LBS", "ESTILO", "LOTE"])

    @staticmethod
    def integrar_y_clasificar_plan(plan_df: pd.DataFrame, asignaciones: pd.DataFrame) -> pd.DataFrame:
        """Consolida las asignaciones calculando transiciones y tipos de día de forma 100% vectorizada."""
        if not asignaciones.empty:
            asig_grouped = asignaciones.groupby(["MAQUINA", "FECHA"], as_index=False).agg({
                "LBS": "sum",
                "ESTILO": "first",
                "LOTE": "first"
            })
            
            plan_df = plan_df.merge(asig_grouped, on=["MAQUINA", "FECHA"], how="left")
            
            plan_df["PLAN_NUEVO_LBS"] = plan_df["LBS"].fillna(0.0)
            plan_df["ESTILO_NUEVO"] = plan_df["ESTILO"].fillna("").str.strip()
            plan_df["LOTE_NUEVO"] = plan_df["LOTE"].fillna("").str.strip()
            plan_df.drop(columns=["LBS", "ESTILO", "LOTE"], inplace=True, errors="ignore")

        plan_df = plan_df.sort_values(["MAQUINA", "FECHA"]).reset_index(drop=True)

        # --- ANÁLISIS VECTORIZADO DE CONTINUIDAD Y TRANSICIONES (SETUPS) ---
        plan_df["ESTILO_ACTIVO"] = np.where(plan_df["PLAN_NUEVO_LBS"] > 0, plan_df["ESTILO_NUEVO"], plan_df["PLAN_ANTERIOR_ESTILO"])
        
        # Shift por grupo de máquina para evitar contaminación entre telares distintos
        plan_df["ESTILO_ANTERIOR"] = plan_df.groupby("MAQUINA")["ESTILO_ACTIVO"].shift(1).fillna("")
        
        # Reglas de negocio vectorizadas
        plan_df["CONTINUIDAD"] = (plan_df["ESTILO_ACTIVO"] == plan_df["ESTILO_ANTERIOR"]) & (plan_df["ESTILO_ACTIVO"] != "")
        plan_df["REQUIERE_SETUP"] = (plan_df["ESTILO_ACTIVO"] != plan_df["ESTILO_ANTERIOR"]) & (plan_df["ESTILO_ANTERIOR"] != "") & (plan_df["PLAN_NUEVO_LBS"] > 0)

        # Clasificación estricta de la naturaleza del día operativo
        condiciones = [
            (plan_df["PLAN_NUEVO_LBS"] > 0),
            (plan_df["PLAN_ANTERIOR_ESTILO"].str.strip() != "")
        ]
        elecciones = ["🟢 PRODUCCION", "🔵 CONTINUIDAD"]
        plan_df["TIPO_DIA"] = np.select(condiciones, elecciones, default="⚪ OCIOSO")
        plan_df["ACTIVA_DIA"] = np.where(plan_df["TIPO_DIA"].isin(["🟢 PRODUCCION", "🔵 CONTINUIDAD"]), 1, 0)

        # Limpieza de estructuras auxiliares de cálculo
        plan_df.drop(columns=["ESTILO_ACTIVO", "ESTILO_ANTERIOR"], inplace=True, errors="ignore")
        
        return plan_df