import streamlit as st
import pandas as pd
import io
from core.services import PlanningOrchestratorService
from core.exceptions import ManufacturingError

st.set_page_config(page_title="Plan Tejido de Avanzada v7", layout="wide")

st.title("🧵 Sistema de Planificación Industrial Avanzada — Tejido")
st.markdown("---")

# File Uploader de la Interfaz de Usuario
uploaded_file = st.file_uploader("Suba el archivo de control de operaciones de planta (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        pestanas_requeridas = {"ESTADO_MAQUINA", "DEMANDA", "PARAMETROS"}
        
        if not pestanas_requeridas.issubset(set(xls.sheet_names)):
            st.error(f"❌ Estructura de archivo inválida. Deben existir las pestañas: {pestanas_requeridas}")
            st.stop()
            
        # Ingesta cruda inicial de datos (asumiendo cabeceras estándar en fila 1)
        estado_raw = pd.read_excel(xls, "ESTADO_MAQUINA", header=1)
        demanda_raw = pd.read_excel(xls, "DEMANDA", header=1)
        params_raw = pd.read_excel(xls, "PARAMETROS", header=1)
        
        # INVOCACIÓN A LA CAPA DE SERVICIO (Desacoplada y protegida por la caché nativa de la UI)
        @st.cache_data(show_spinner="Ejecutando asignaciones y validaciones del core de ingeniería...")
        def _cached_pipeline(df_e, df_d, df_p):
            return PlanningOrchestratorService.ejecutar_pipeline_industrial(df_e, df_d, df_p)
            
        plan, kpis, pivot = _cached_pipeline(estado_raw, demanda_raw, params_raw)
        
        # ============================================================
        # VISUALIZACIÓN DE CUADROS DE MANDO E INDICADORES KPI
        # ============================================================
        st.subheader("⚙️ Métricas de Rendimiento Operativo del Plan")
        m1, m2, m3, m4 = st.columns(4)
        
        total_lbs = plan["PLAN_NUEVO_LBS"].sum()
        total_setups = plan["REQUIERE_SETUP"].sum()
        max_maqs = kpis["MAQS_ACTIVAS"].max()
        total_maquinas_unicas = len(plan["MAQUINA"].unique())
        eficiencia_uso = (kpis["MAQS_ACTIVAS"].mean() / total_maquinas_unicas) * 100 if total_maquinas_unicas > 0 else 0
        
        m1.metric("Libras Planificadas", f"{total_lbs:,.1f} Lbs", help="Carga de tejido total inyectada")
        m2.metric("Eficiencia de Ocupación Promedio", f"{eficiencia_uso:.1f} %", help="Uso promedio de la capacidad instalada")
        m3.metric("Picos de Máquinas Activas", f"{max_maqs} Máqs", help="Máxima cantidad de telares operando simultáneamente")
        m4.metric("Paradas por Set-up", f"{total_setups} Cambios", delta=int(total_setups), delta_color="inverse", help="Veces que se detendrá una máquina a cambiar estilo/lote")
        
        # Control de Pestañas Visuales
        tabs = st.tabs(["📋 Plan de Trabajo Diario", "📊 Matriz de Distribución (Estilo Excel)", "📈 Capacidad e Impacto Operativo"])
        
        with tabs[0]:
            st.dataframe(plan, use_container_width=True, height=400)
            
        with tabs[1]:
            st.dataframe(pivot, use_container_width=True, height=400)
            
        with tabs[2]:
            st.markdown("#### Balance de Carga de Planta por Día")
            st.line_chart(kpis.set_index("FECHA"))
            
        # Generación segura de binario de descarga Excel sin manipulación local de IO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            plan.to_excel(writer, index=False, sheet_name="PLAN_DIARIO")
            kpis.to_excel(writer, index=False, sheet_name="METRICAS_DIARIAS")
            pivot.to_excel(writer, sheet_name="PIVOT_MATRIZ")
            
        st.download_button(
            label="📥 Descargar Plan Industrial Validado (.xlsx)",
            data=output.getvalue(),
            file_name="PLAN_TEJIDO_AVANZADO_VALIDADO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except ManufacturingError as me:
        st.error(f"🚨 Error de validación industrial: {str(me)}")
    except Exception as e:
        st.error(f"🚨 Error crítico inesperado: {str(e)}")
        st.info("Por favor, póngase en contacto con el departamento de TI e Ingeniería de Procesos.")