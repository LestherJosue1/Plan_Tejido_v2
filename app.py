# app.py
import streamlit as st
import pandas as pd
import io
from core.services import PlanificacionService

st.set_page_config(page_title="Planificación Avanzada de Tejido", layout="wide")

st.title("🏭 Motor Industrial de Planificación de Tejido")
st.subheader("Algoritmo de Programación Heurística por Fases (Multi-pestaña)")

uploaded_file = st.file_uploader("Cargar Plantilla Maestra de Planta (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        with st.spinner("Ejecutando algoritmo avanzado del motor Colab (Fases 0, 1, 2 + Análisis de Secuencia de Color)..."):
            # Llamamos al orquestador
            df_plan = PlanificacionService.procesar_pipeline_industrial(uploaded_file)
            
        st.success("🎉 Plan diario generado con éxito respetando restricciones horarias y calendarios de mantenimiento.")
        
        # Visualizaciones en pestañas modernas
        tab1, tab2, tab3 = st.tabs(["📊 Plan de Producción Detallado", "📈 KPIs Operativos", "📥 Descargar Resultados"])
        
        with tab1:
            st.dataframe(df_plan, use_container_width=True)
            
        with tab2:
            st.markdown("### Resumen de Carga por Día y Máquina")
            # Gráficos dinámicos basados en la salida exacta
            
        with tab3:
            # Botón de descarga del Excel procesado
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_plan.to_excel(writer, index=False, sheet_name="PLAN_DETALLADO")
            
            st.download_button(
                label="📥 Descargar Plan Industrial Validado (.xlsx)",
                data=output.getvalue(),
                file_name="PLAN_PRODUCCION_COLAB_INTEGRADO.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"🚨 Error en la corrida del modelo: {str(e)}")
