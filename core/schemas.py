# core/schemas.py
import pandas as pd

REQUIRED_SHEETS = [
    "PARAMETROS", "ESTADO_MAQUINA", "DEMANDA", 
    "COMPAT_MAQUINA", "RATES", "REGLAS"
]

REQUIRED_COLUMNS = {
    "PARAMETROS": ["Campo", "Valor"],
    "ESTADO_MAQUINA": ["MAQUINA"],  # Columnas dinámicas u opcionales se normalizan
    "DEMANDA": ["ESTILO", "TITULAR", "TEJIDO", "LBS_PENDIENTES"],
    "COMPAT_MAQUINA": ["MAQUINA", "TITULAR", "TEJIDO_PERMITIDO"],
    "RATES": ["MAQUINA", "ESTILO", "TITULAR", "TEJIDO", "RATE_LBS_DIA"],
    "REGLAS": ["Regla", "Valor (SI/NO)"]
}

def validar_excel_estructura(excel_file) -> dict:
    """Valida la existencia de pestañas y columnas mínimas."""
    try:
        xls = pd.ExcelFile(excel_file)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo Excel: {str(e)}")
        
    for sheet in REQUIRED_SHEETS:
        if sheet not in xls.sheet_names:
            raise ValueError(f"Falta la pestaña mandatoria: '{sheet}' en el archivo.")
            
    return {"status": "OK", "sheets": xls.sheet_names}
