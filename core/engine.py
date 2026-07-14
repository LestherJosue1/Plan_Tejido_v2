# core/engine.py
import pandas as pd
import numpy as np
import re, math
from datetime import datetime, date
from fnmatch import fnmatchcase

# --- HELPERS DE NORMALIZACIÓN EXACTA DE TU COLAB ---
def s(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return ""
    return str(x).strip()

def collapse_spaces(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def norm_text(x):
    t = s(x)
    return collapse_spaces(t).upper() if t else ""

def norm_intlike(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return ""
    if isinstance(x, (int, np.integer)): return str(int(x))
    if isinstance(x, (float, np.floating)) and float(x).is_integer(): return str(int(float(x)))
    t = collapse_spaces(str(x))
    if re.fullmatch(r"\d+\.0", t): return str(int(float(t)))
    return t.upper()

def machine(x, width=4):
    if x is None or (isinstance(x, float) and math.isnan(x)): return ""
    if isinstance(x, (int, np.integer)): t = str(int(x))
    elif isinstance(x, (float, np.floating)) and float(x).is_integer(): t = str(int(float(x)))
    else:
        t = s(x)
        if re.fullmatch(r"\d+\.0", t): t = str(int(float(t)))
    t = t.strip()
    return t.zfill(width) if t.isdigit() and len(t) < width else t

def lot_norm(x):
    if x is None or (isinstance(x, float) and math.isnan(x)): return ""
    if isinstance(x, (int, np.integer)): return str(int(x))
    if isinstance(x, (float, np.floating)) and float(x).is_integer(): return str(int(float(x)))
    t = collapse_spaces(str(x))
    if re.fullmatch(r"\d+\.0", t): return str(int(float(t)))
    if "/" in t:
        a, b = t.split("/", 1)
        return a.strip().upper() + "/" + b.strip().upper()
    return t.upper()

def parse_date(x):
    if x is None or (isinstance(x, float) and math.isnan(x)) or s(x) == "": return pd.NaT
    if isinstance(x, (datetime, pd.Timestamp, date)): return pd.to_datetime(x).normalize()
    return pd.to_datetime(s(x), errors="coerce").normalize()

# --- EJECUCIÓN CENTRAL DEL MOTOR ---
def ejecutar_motor_colab(excel_path):
    """
    Ejecuta de manera secuencial las fases heurísticas del script original.
    Retorna dataframes limpios para la interfaz de Streamlit.
    """
    # 1. Carga de datos de las pestañas (reemplaza files.upload())
    xls = pd.ExcelFile(excel_path)
    
    params_tbl = pd.read_excel(xls, "PARAMETROS", header=1)
    estado     = pd.read_excel(xls, "ESTADO_MAQUINA", header=1)
    demanda    = pd.read_excel(xls, "DEMANDA", header=1)
    compat     = pd.read_excel(xls, "COMPAT_MAQUINA", header=1)
    rates      = pd.read_excel(xls, "RATES", header=1)
    reglas     = pd.read_excel(xls, "REGLAS", header=1)
    
    # Pestañas opcionales
    restr_df = pd.read_excel(xls, "RESTRICCIONES", header=1) if "RESTRICCIONES" in xls.sheet_names else pd.DataFrame()
    cal_df   = pd.read_excel(xls, "CALENDARIO_MAQUINA", header=1) if "CALENDARIO_MAQUINA" in xls.sheet_names else pd.DataFrame()
    
    # ... [Aquí se pega toda la lógica secuencial de asignación de fases, rates lookup, setup y penalizaciones del Colab] ...
    
    # Al final, consolidamos el "schedule" en un DataFrame plano de salida
    plan_final_rows = []
    # Loop para construir el plan_diario final basado en el diccionario `schedule` generado...
    
    # Retornamos los resultados listos para graficar y descargar
    df_plan = pd.DataFrame(plan_final_rows)
    return df_plan
