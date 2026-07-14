import pandas as pd
from typing import Tuple, Dict

class DataValidator:
    """Valida la estructura y consistencia de las pestañas del Excel industrial."""
    
    REQUIRED_SHEETS = ["PARAMETROS", "ESTADO_MAQUINA", "DEMANDA", "COMPAT_MAQUINA", "RATES", "REGLAS"]

    @classmethod
    def validate_and_load(cls, excel_file) -> Dict[str, pd.DataFrame]:
        try:
            xls = pd.ExcelFile(excel_file)
        except Exception as e:
            raise ValueError(f"No se pudo decodificar el archivo Excel: {str(e)}")
            
        for sheet in cls.REQUIRED_SHEETS:
            if sheet not in xls.sheet_names:
                raise ValueError(f"Estructura inválida. Falta la pestaña mandatoria: '{sheet}'")
                
        # Lectura limpia (asumiendo encabezados en la primera fila real, header=0)
        dfs = {
            "PARAMETROS": pd.read_excel(xls, "PARAMETROS", header=0),
            "ESTADO_MAQUINA": pd.read_excel(xls, "ESTADO_MAQUINA", header=0),
            "DEMANDA": pd.read_excel(xls, "DEMANDA", header=0),
            "COMPAT_MAQUINA": pd.read_excel(xls, "COMPAT_MAQUINA", header=0),
            "RATES": pd.read_excel(xls, "RATES", header=0),
            "REGLAS": pd.read_excel(xls, "REGLAS", header=0),
        }
        
        # Pestañas condicionales u opcionales de la planta
        dfs["RESTRICCIONES"] = pd.read_excel(xls, "RESTRICCIONES", header=0) if "RESTRICCIONES" in xls.sheet_names else pd.DataFrame()
        dfs["CALENDARIO_MAQUINA"] = pd.read_excel(xls, "CALENDARIO_MAQUINA", header=0) if "CALENDARIO_MAQUINA" in xls.sheet_names else pd.DataFrame()
        
        return dfs
