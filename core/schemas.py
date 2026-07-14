import pandas as pd
from typing import Tuple, List
from core.exceptions import InvalidSchemaError

class DataValidator:
    """Valida y normaliza de forma estricta los datos ingresados a la planta."""
    
    REQUIRED_ESTADO = {"MAQUINA", "ESTILO_REAL", "LOTE_HILO"}
    REQUIRED_DEMANDA = {"ESTILO_OPTIMO", "LOTE_HILO", "LBS_PENDIENTES"}
    REQUIRED_PARAMS = {"Campo", "Valor"}

    @classmethod
    def validate_and_clean(
        cls, df_estado: pd.DataFrame, df_demanda: pd.DataFrame, df_params: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Asegura la calidad de datos y normaliza tipos de forma vectorizada."""
        
        if not cls.REQUIRED_ESTADO.issubset(df_estado.columns):
            raise InvalidSchemaError(f"Faltan columnas críticas en ESTADO_MAQUINA: {cls.REQUIRED_ESTADO - set(df_estado.columns)}")
        if not cls.REQUIRED_DEMANDA.issubset(df_demanda.columns):
            raise InvalidSchemaError(f"Faltan columnas críticas en DEMANDA: {cls.REQUIRED_DEMANDA - set(df_demanda.columns)}")
        if not cls.REQUIRED_PARAMS.issubset(df_params.columns):
            raise InvalidSchemaError(f"Faltan columnas críticas en PARAMETROS: {cls.REQUIRED_PARAMS - set(df_params.columns)}")

        # Copias profundas operacionales
        estado = df_estado.copy()
        demanda = df_demanda.copy()
        params = df_params.copy()

        # Normalización estricta de IDs de máquinas (Padding a 4 dígitos de forma segura)
        estado["MAQUINA"] = estado["MAQUINA"].dropna().astype(float).astype(int).astype(str).str.zfill(4)
        estado["ESTILO_REAL"] = estado["ESTILO_REAL"].astype(str).str.strip()
        estado["LOTE_HILO"] = estado["LOTE_HILO"].astype(str).str.strip()

        # Normalización de Demanda
        demanda["ESTILO_OPTIMO"] = demanda["ESTILO_OPTIMO"].astype(str).str.strip()
        demanda["LOTE_HILO"] = demanda["LOTE_HILO"].astype(str).str.strip()
        demanda["LBS_PENDIENTES"] = pd.to_numeric(demanda["LBS_PENDIENTES"], errors="coerce").fillna(0.0)

        # Normalización de Parámetros
        params["Campo"] = params["Campo"].astype(str).str.strip()

        return estado, demanda, params