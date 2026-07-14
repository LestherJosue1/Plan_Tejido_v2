import pandas as pd
import numpy as np
import re
import math
from datetime import datetime, date
from fnmatch import fnmatchcase

# --- HELPERS DE NORMALIZACIÓN ULTRA-PRECISA DEL SCRIPT DE COLAB ---
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


class ProductionEngineColab:
    """Implementación limpia del algoritmo por fases, transiciones y compatibilidades del piso de producción."""
    
    @staticmethod
    def ejecutar_planificacion(dfs: dict) -> pd.DataFrame:
        # --- PARSEO DE PARÁMETROS OPERATIVOS ---
        p_dict = {}
        for _, r in dfs["PARAMETROS"].iterrows():
            k = norm_text(r.get("Campo"))
            if k: p_dict[k] = r.get("Valor")
            
        f_ini = parse_date(p_dict.get("FECHA_INICIO_PLAN"))
        f_fin = parse_date(p_dict.get("FECHA_FIN_PLAN"))
        if pd.isna(f_ini) or pd.isna(f_fin):
            raise ValueError("Las fechas de inicio o fin del plan en PARAMETROS son inválidas.")
            
        fechas_horizonte = pd.date_range(f_ini, f_fin).normalize().tolist()
        
        # Carga de penalizaciones horarias por setups (Reglas)
        r_dict = {}
        for _, r in dfs["REGLAS"].iterrows():
            k = norm_text(r.get("Regla"))
            if k: r_dict[k] = r.get("Valor (SI/NO)")
            
        hrs_setup_estilo = float(r_dict.get("HRS_SETUP_ESTILO", 8.0))
        hrs_setup_lote   = float(r_dict.get("HRS_SETUP_LOTE", 4.0))
        hrs_setup_color  = float(r_dict.get("HRS_SETUP_COLOR", 6.0))
        
        # --- PREPARACIÓN DE MAQUINARIAS ---
        maquinas_list = []
        for _, r in dfs["ESTADO_MAQUINA"].iterrows():
            m_id = machine(r.get("MAQUINA"))
            if not m_id: continue
            maquinas_list.append({
                "MAQUINA": m_id,
                "ESTILO_ACTIVO": norm_text(r.get("ESTILO_OPTIMO")),
                "LOTE_ACTIVO": lot_norm(r.get("LOTE_HILO")),
                "COLOR_ACTIVO": norm_text(r.get("COLOR")),
                "COMPONENTE_COLOR_ACTIVO": norm_text(r.get("COMPONENTE_COLOR"))
            })
            
        # --- MATRIZ DE CALENDARIO Y PAROS ---
        paros_set = set()
        if not dfs["CALENDARIO_MAQUINA"].empty:
            for _, r in dfs["CALENDARIO_MAQUINA"].iterrows():
                m_id = machine(r.get("MAQUINA"))
                dt = parse_date(r.get("FECHA"))
                if m_id and not pd.isna(dt):
                    paros_set.add((m_id, dt))

        # --- MATRIZ DE TARIFAS (RATES) ---
        rates_dict = {}
        for _, r in dfs["RATES"].iterrows():
            m_id = machine(r.get("MAQUINA"))
            est = norm_text(r.get("ESTILO"))
            rate = pd.to_numeric(r.get("RATE_LBS_DIA"), errors="coerce")
            if m_id and est and not pd.isna(rate):
                rates_dict[(m_id, est)] = float(rate)

        # --- COMPATIBILIDADES ---
        compat_dict = {}
        for _, r in dfs["COMPAT_MAQUINA"].iterrows():
            m_id = machine(r.get("MAQUINA"))
            tit = norm_text(r.get("TITULAR"))
            tej = norm_text(r.get("TEJIDO_PERMITIDO"))
            if m_id:
                compat_dict.setdefault(m_id, []).append({"TITULAR": tit, "TEJIDO": tej})

        # --- INGESTIÓN Y ORDENAMIENTO DE DEMANDA ---
        demanda_items = []
        for idx, r in dfs["DEMANDA"].iterrows():
            lbs = pd.to_numeric(r.get("LBS_PENDIENTES"), errors="coerce")
            if pd.isna(lbs) or lbs <= 0: continue
            demanda_items.append({
                "ID": idx,
                "ESTILO": norm_text(r.get("ESTILO")),
                "TITULAR": norm_text(r.get("TITULAR")),
                "TEJIDO": norm_text(r.get("TEJIDO")),
                "LOTE": lot_norm(r.get("LOTE_HILO")),
                "COLOR": norm_text(r.get("COLOR")),
                "COMPONENTE_COLOR": norm_text(r.get("COMPONENTE_COLOR")),
                "LBS_PENDIENTES": float(lbs),
                "PRIORIDAD": int(r.get("PRIORIDAD", 99))
            })
            
        # --- INICIALIZACIÓN DEL ESTADO DE CONTROL DE CADA TELAR ---
        schedule = {m["MAQUINA"]: {} for m in maquinas_list}
        maquina_estado_actual = {m["MAQUINA"]: m for m in maquinas_list}

        # --- EJECUCIÓN SÍNCRONA DE FASES HEURÍSTICAS DE PRODUCCIÓN ---
        for f_date in fechas_horizonte:
            for m_info in maquinas_list:
                m_id = m_info["MAQUINA"]
                
                # Control de Paros de Planta
                if (m_id, f_date) in paros_set:
                    schedule[m_id][f_date] = {
                        "LBS": 0.0, "ESTILO": "", "LOTE": "", "COLOR": "", 
                        "COMPONENTE_COLOR": "", "TIPO_DIA": "⚪ PARO_MANTENIMIENTO", "HRS_DISP": 0.0
                    }
                    continue
                    
                # Inicializar el día operativo (24 horas)
                hrs_disponibles = 24.0
                est_act = maquina_estado_actual[m_id]["ESTILO_ACTIVO"]
                lot_act = maquina_estado_actual[m_id]["LOTE_ACTIVO"]
                col_act = maquina_estado_actual[m_id]["COLOR_ACTIVO"]
                cc_act  = maquina_estado_actual[m_id]["COMPONENTE_COLOR_ACTIVO"]
                
                lbs_producidas_hoy = 0.0
                estilo_hoy, lote_hoy, color_hoy, cc_hoy = est_act, lot_act, col_act, cc_act
                dia_asignado = False

                # Filtrar demandas compatibles con la máquina física
                req_compatibles = []
                for d in demanda_items:
                    if d["LBS_PENDIENTES"] <= 0: continue
                    # Filtrar por Matriz de Compatibilidad
                    comp_rules = compat_dict.get(m_id, [])
                    is_compat = False
                    for rule in comp_rules:
                        if (rule["TITULAR"] == "*" or fnmatchcase(d["TITULAR"], rule["TITULAR"])) and \
                           (rule["TEJIDO"] == "*" or fnmatchcase(d["TEJIDO"], rule["TEJIDO"])):
                            is_compat = True
                            break
                    if is_compat: req_compatibles.append(d)

                # FASE 0: Continuidad de Carga Heredada (Misma estructura)
                if est_act:
                    match_cont = [d for d in req_compatibles if d["ESTILO"] == est_act and d["LOTE"] == lot_act]
                    if match_cont:
                        match_cont.sort(key=lambda x: x["PRIORIDAD"])
                        target = match_cont[0]
                        rate_dia = rates_dict.get((m_id, target["ESTILO"]), 500.0)
                        rate_hora = rate_dia / 24.0
                        
                        max_lbs_hoy = hrs_disponibles * rate_hora
                        prod = min(max_lbs_hoy, target["LBS_PENDIENTES"])
                        
                        hrs_usadas = prod / rate_hora if rate_hora > 0 else 0
                        hrs_disponibles -= hrs_usadas
                        target["LBS_PENDIENTES"] -= prod
                        lbs_producidas_hoy += prod
                        dia_asignado = True

                # FASE 1 & FASE 2: Transición a Cargas Nuevas (Con penalización horaria por Set-ups)
                if hrs_disponibles > 1.0 and req_compatibles:
                    # Ordenar por Prioridad del negocio y luego por volumen
                    req_compatibles.sort(key=lambda x: (x["PRIORIDAD"], -x["LBS_PENDIENTES"]))
                    
                    for target in req_compatibles:
                        if target["LBS_PENDIENTES"] <= 0: continue
                        
                        # Cálculo Dinámico de Tiempos de Cambio (Setup Deductions)
                        penalizacion = 0.0
                        if target["ESTILO"] != est_act and est_act != "": penalizacion += hrs_setup_estilo
                        if target["LOTE"] != lot_act and lot_act != "": penalizacion += hrs_setup_lote
                        if target["COLOR"] != col_act and col_act != "": penalizacion += hrs_setup_color
                        
                        if hrs_disponibles > penalizacion:
                            hrs_disponibles -= penalizacion
                            rate_dia = rates_dict.get((m_id, target["ESTILO"]), 500.0)
                            rate_hora = rate_dia / 24.0
                            
                            max_lbs_hoy = hrs_disponibles * rate_hora
                            prod = min(max_lbs_hoy, target["LBS_PENDIENTES"])
                            
                            hrs_usadas = prod / rate_hora if rate_hora > 0 else 0
                            hrs_disponibles -= hrs_usadas
                            target["LBS_PENDIENTES"] -= prod
                            lbs_producidas_hoy += prod
                            
                            estilo_hoy, lote_hoy, color_hoy, cc_hoy = target["ESTILO"], target["LOTE"], target["COLOR"], target["COMPONENTE_COLOR"]
                            dia_asignado = True
                            break # Cierra asignación de celda diaria

                # Consolidación de Estados de Máquina del día evaluado
                if lbs_producidas_hoy > 0:
                    schedule[m_id][f_date] = {
                        "LBS": lbs_producidas_hoy, "ESTILO": estilo_hoy, "LOTE": lote_hoy,
                        "COLOR": color_hoy, "COMPONENTE_COLOR": cc_hoy, "TIPO_DIA": "🟢 PRODUCCION", "HRS_DISP": hrs_disponibles
                    }
                    maquina_estado_actual[m_id].update({
                        "ESTILO_ACTIVO": estilo_hoy, "LOTE_ACTIVO": lote_hoy, 
                        "COLOR_ACTIVO": color_hoy, "COMPONENTE_COLOR_ACTIVO": cc_hoy
                    })
                else:
                    schedule[m_id][f_date] = {
                        "LBS": 0.0, "ESTILO": est_act, "LOTE": lot_act, 
                        "COLOR": col_act, "COMPONENTE_COLOR": cc_act, "TIPO_DIA": "🔵 OCIOSO_CON_ESTILO", "HRS_DISP": hrs_disponibles
                    }

        # --- TRANSFORMACIÓN A DATAFRAME DE PRODUCCIÓN DE SALIDA ---
        registros_salida = []
        for m_id, dias in schedule.items():
            for f_date, info in dias.items():
                registros_salida.append({
                    "MAQUINA": m_id,
                    "FECHA": f_date.strftime("%Y-%m-%d"),
                    "PLAN_NUEVO_LBS": info["LBS"],
                    "ESTILO_NUEVO": info["ESTILO"],
                    "LOTE_NUEVO": info["LOTE"],
                    "COLOR_NUEVO": info["COLOR"],
                    "COMPONENTE_COLOR_NUEVO": info["COMPONENTE_COLOR"],
                    "TIPO_DIA": info["TIPO_DIA"],
                    "HORAS_RESTANTES": info["HRS_DISP"]
                })
                
        return pd.DataFrame(registros_salida)
