import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="GuardianAI - Acelerador de Compliance",
    page_icon="🛡️",
    layout="wide"
)

# --- Título y Estilo ---
st.markdown("<h1 style='text-align: center; color: #0072B1;'>🛡️ GuardianAI</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Acelerador de Compliance para Dicsys (PoC)</h3>", unsafe_allow_html=True)
st.markdown("---")

# --- Configuración de la API ---
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("GUARDIAN_API_KEY")

if not API_URL or not API_KEY:
    st.error("Error de configuración: Faltan las variables de entorno API_URL o GUARDIAN_API_KEY.")
    st.stop()

# --- Formulario de Interacción ---
st.subheader("Realice su consulta de compliance:")
with st.form(key="compliance_form"):
    query_text = st.text_area(
        "Escriba su pregunta o situación:",
        height=150,
        placeholder="Ej: Soy el Gerente de TI de un retail mediano en Chile. Dame una hoja de ruta con los tres primeros pasos que debo tomar en los próximos 6 meses para prepararme para la Ley 21.719."
    )
    submit_button = st.form_submit_button(label="Generar Análisis 🚀")

# --- Lógica de la Aplicación ---
if submit_button and query_text:
    with st.spinner("🧠 Analizando normativas y conocimiento experto... por favor espere."):
        try:
            headers = {"x-api-key": API_KEY}
            payload = {"text": query_text, "user_id": "streamlit_user"}
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            
            response.raise_for_status()
            
            result = response.json()

            st.markdown("---")
            st.subheader("📄 Reporte de Análisis de Compliance")
            st.markdown(result["analysis"])

            with st.expander("🔬 Ver Detalles Técnicos y Fuentes Utilizadas"):
                st.success("Análisis completado exitosamente.")
                
                st.subheader("📊 Métricas de Consumo")
                token_usage = result.get("token_usage", {})
                st.metric(label="Tokens Totales", value=f"{token_usage.get('total_tokens', 0):,}")

                st.subheader("📚 Fuentes Recuperadas del Contexto")
                sources = result.get("sources", [])
                for i, source in enumerate(sources):
                    st.markdown(f"**Fuente #{i+1}:** `{source.get('source_document', 'N/A')}`")
                    st.text_area(f"Contenido #{i+1}", value=source.get('content_chunk', ''), height=150, disabled=True)
                
                st.subheader("🔗 Trazabilidad")
                st.info(f"**Trace ID:** `{result.get('trace_id', 'N/A')}`")

        except requests.exceptions.HTTPError as http_err:
            error_detail = http_err.response.json().get("detail", http_err)
            st.error(f"Error de la API ({http_err.response.status_code}): {error_detail}")
        except requests.exceptions.RequestException as e:
            st.error(f"Ocurrió un error de conexión: {e}")
elif submit_button:
    st.warning("Por favor, ingrese una consulta.")