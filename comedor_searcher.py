import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from datetime import datetime
import re
import os
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="🍽️ Buscador de Comedores Comunitarios",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ID del Google Sheet
GOOGLE_SHEET_ID = "1svD6kfWvI9GTNzoqIhmSNa80MfGpjWqwQJRxOLxXOXI"

# Función para obtener el ID del Google Sheet
def get_google_sheet_id():
    """Obtiene el ID del Google Sheet desde secrets o usa el valor por defecto"""
    try:
        if "google_sheet" in st.secrets and "sheet_id" in st.secrets["google_sheet"]:
            return st.secrets["google_sheet"]["sheet_id"]
        else:
            return GOOGLE_SHEET_ID
    except:
        return GOOGLE_SHEET_ID

# Configuración de las pestañas
SHEET_CONFIG = {
    "INGRESO_COMEDORES": {
        "name": "🏠 Ingreso de Comedores",
        "search_column": "nombre_comedor",
        "area": "SANEAMIENTO",
        "proposito": "Verificar el cumplimiento de condiciones para el ingreso del comedor al Proyecto Comedores Comunitarios.",
        "dashboard": None
    },
    "CEDECO": {
        "name": "🏢 CEDECO",
        "search_column": "NOMBRE_COMEDOR",
        "area": "PROYECTO NUEVO DE COMEDORES COMUNITARIOS INTEGRALES",
        "proposito": "Bitácora de visitas de reconocimiento de comedores preseleccionados para vincularse como centros de desarrollo comunitario.",
        "dashboard": "https://cedeco-2025.streamlit.app/"
    },
    "DIOR": {
        "name": "👥 DIOR",
        "search_column": "NOMBRE_COMEDOR",
        "area": "GESTIÓN HUMANA",
        "proposito": "Evaluar el clima organizacional al interior del comedor comunitario, desde la percepción de las gestoras/es para comprender el nivel de relacionamiento, el trabajo en equipo, los liderazgos y el sentido de pertenencia que se vive en el comedor, a partir de la aplicación de una encuesta dirigida a las gestoras/es, de tal manera que nos permita identificar las condiciones que favorecen o dificultan su funcionamiento.",
        "dashboard": "https://dior25.streamlit.app/"
    },
    "DUB": {
        "name": "📊 DUB",
        "search_column": "Nombre_comedor",
        "area": "CARACTERIZACIÓN",
        "proposito": "Caracterización de grupos poblacionales y poblaciones vulnerables del Distrito de Santiago de Cali, a fin de obtener información detallada y precisa sobre las características demográficas, socioeconómicas, culturales y de salud de estas poblaciones.",
        "dashboard": "https://dupstory.streamlit.app/"
    },
    "ENCUESTA": {
        "name": "📝 Encuesta",
        "search_column": "nombre_comedor",
        "area": "NUTRICIÓN",
        "proposito": "Mantener los estándares de calidad diseñados por el proyecto para la entrega de los insumos y/o productos alimentarios, ajustando de manera permanente su accionar al cumplimiento del objetivo dirigido a propiciar el acceso a los alimentos de la población en situación de pobreza monetaria extrema.",
        "dashboard": "https://satisfaccionutri-qoke9iuewruoyyvebeueci.streamlit.app/"
    },
    "VERCOAL": {
        "name": "🚚 VERCOAL",
        "search_column": "nombre_comedor",
        "area": "LOGÍSTICA",
        "proposito": "Verificación de condiciones en la entrega de insumos alimentarios a los comedores comunitarios.",
        "dashboard": "https://vercoal.streamlit.app/cumplimiento"
    }
}

# Función para cargar credenciales de Google Sheets
@st.cache_resource
def load_google_credentials():
    """Carga las credenciales de Google desde archivo JSON (local) o secrets (Streamlit Cloud)"""
    try:
        # Intentar cargar desde Streamlit secrets (para producción)
        if "google_credentials" in st.secrets:
            credentials_dict = dict(st.secrets["google_credentials"])
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets"
            ]
            credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
            return credentials
        
        # Intentar cargar desde archivo local (para desarrollo)
        elif os.path.exists('google_credentials.json'):
            credentials_path = 'google_credentials.json'
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets"
            ]
            credentials = Credentials.from_service_account_file(credentials_path, scopes=scope)
            return credentials
        
        else:
            st.error("❌ No se encontraron credenciales de Google")
            st.info("💡 Para desarrollo local: agrega 'google_credentials.json'")
            st.info("💡 Para Streamlit Cloud: configura los secrets")
            return None
            
    except Exception as e:
        st.error(f"❌ Error cargando credenciales: {str(e)}")
        return None

@st.cache_resource
def connect_to_google_sheets():
    """Conecta a Google Sheets y retorna el workbook"""
    try:
        # Cargar credenciales desde archivo JSON o secrets
        credentials = load_google_credentials()
        if credentials is None:
            return None
            
        # Autorizar cliente con gspread
        client = gspread.authorize(credentials)
        sheet_id = get_google_sheet_id()
        workbook = client.open_by_key(sheet_id)
        return workbook
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ No se pudo encontrar el Google Sheet. Verifica el ID del documento.")
        return None
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Error de API de Google Sheets: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {str(e)}")
        st.info("💡 Intenta refrescar la página o verifica las credenciales")
        return None

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    """Carga los datos de una pestaña específica"""
    try:
        workbook = connect_to_google_sheets()
        if workbook is None:
            return None
        
        # Verificar si la hoja existe
        try:
            worksheet = workbook.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"❌ No se encontró la pestaña '{sheet_name}' en el Google Sheet")
            return None
            
        # Obtener todos los datos
        try:
            data = worksheet.get_all_records(empty_value='', default_blank='')
        except Exception as e:
            # Fallback: obtener datos como valores y crear DataFrame manualmente
            # st.info(f"🔄 Cargando {sheet_name} con método alternativo...")
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                st.warning(f"⚠️ La pestaña {sheet_name} parece estar vacía")
                return None
            
            headers = all_values[0]
            data_rows = all_values[1:]
            data = []
            for row in data_rows:
                # Asegurar que la fila tenga el mismo número de columnas que los headers
                while len(row) < len(headers):
                    row.append('')
                row_dict = dict(zip(headers, row))
                data.append(row_dict)
        
        if data:
            df = pd.DataFrame(data)
            # Limpiar DataFrame: remover filas completamente vacías
            df = df.dropna(how='all')
            return df
        else:
            st.warning(f"⚠️ No se encontraron datos en la pestaña {sheet_name}")
            return None
            
    except Exception as e:
        st.error(f"❌ Error cargando datos de {sheet_name}: {str(e)}")
        return None

def normalize_text(text):
    """Normaliza el texto para búsqueda"""
    if pd.isna(text) or text == "":
        return ""
    text = str(text).lower().strip()
    # Remover acentos y caracteres especiales
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    return text

def search_in_dataframe(df, search_column, search_term):
    """Busca en un DataFrame específico"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    if search_column not in df.columns:
        return pd.DataFrame()
    
    search_term_normalized = normalize_text(search_term)
    
    # Crear una máscara de búsqueda
    mask = df[search_column].astype(str).apply(normalize_text).str.contains(search_term_normalized, na=False)
    
    return df[mask]
def display_record_card(record, sheet_name):
    """Muestra una tarjeta con la información del registro"""
    config = SHEET_CONFIG[sheet_name]
    
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #ddd; 
            border-radius: 10px; 
            padding: 15px; 
            margin: 10px 0; 
            background-color: #f9f9f9;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {config['name']}")
        
        with col2:
            st.markdown(f"**Tabla:** `{sheet_name}`")
        
        # Mostrar información del área y propósito
        st.markdown(f"**🏢 Área:** {config['area']}")
        if config['dashboard']:
            st.markdown(f"**📈 Dashboard:** [{config['dashboard']}]({config['dashboard']})")
        
        # Mostrar algunos campos importantes del registro
        search_col = config['search_column']
        if search_col in record.index and pd.notna(record[search_col]):
            st.markdown(f"**🍽️ Comedor:** {record[search_col]}")
        
        # Mostrar otros campos relevantes (primeros 6 campos no vacíos)
        shown_fields = 0
        cols = st.columns(2)
        for field, value in record.items():
            if shown_fields >= 6:
                break
            if field != search_col and pd.notna(value) and str(value).strip() != "":
                with cols[shown_fields % 2]:
                    st.markdown(f"**{field}:** {value}")
                shown_fields += 1
        
        # Expandir para ver todos los datos
        with st.expander("Ver todos los datos", expanded=False):
            for field, value in record.items():
                if pd.notna(value) and str(value).strip() != "":
                    st.text(f"{field}: {value}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def get_all_comedores():
    """Obtiene una lista de todos los comedores únicos"""
    all_comedores = set()
    
    for sheet_name, config in SHEET_CONFIG.items():
        df = load_sheet_data(sheet_name)
        if df is not None and not df.empty:
            search_column = config["search_column"]
            if search_column in df.columns:
                comedores = df[search_column].dropna().astype(str).str.strip()
                comedores = comedores[comedores != ""]
                all_comedores.update(comedores.tolist())
    
    return sorted(list(all_comedores))

# ==========================================
# AGENTE DE INTELIGENCIA ARTIFICIAL
# ==========================================

class ComedorAIAgent:
    def __init__(self, sheet_config, load_sheet_data_func):
        self.sheet_config = sheet_config
        self.load_sheet_data = load_sheet_data_func
        self.conversation_history = []
    
    def process_query(self, user_query):
        """Procesa la consulta del usuario usando lógica de NLP básica"""
        query_lower = user_query.lower()
        
        # Detectar el nombre del comedor
        comedor_name = self._extract_comedor_name(query_lower)
        
        # Detectar tipo de consulta
        query_type = self._detect_query_type(query_lower)
        
        # Procesar según el tipo
        if query_type == "search_comedor":
            return self._search_comedor_info(comedor_name, user_query)
        elif query_type == "compare_data":
            return self._compare_comedor_data(comedor_name, user_query)
        elif query_type == "statistics":
            return self._generate_statistics(comedor_name, user_query)
        elif query_type == "cross_analysis":
            return self._cross_analysis(comedor_name, user_query)
        else:
            return self._general_search(user_query)
    
    def _extract_comedor_name(self, query):
        """Extrae el nombre del comedor de la consulta"""
        # Patrones comunes para identificar nombres de comedores
        patterns = [
            r"comedor\s+([a-záéíóúñ\s]+?)(?:\s|$|,|\?|\.)",
            r"del\s+([a-záéíóúñ\s]+?)(?:\s|$|,|\?|\.)",
            r"llamado\s+([a-záéíóúñ\s]+?)(?:\s|$|,|\?|\.)",
            r"nombre\s+([a-záéíóúñ\s]+?)(?:\s|$|,|\?|\.)",
            r"([a-záéíóúñ\s]{3,})(?:\s|$|,|\?|\.)"  # Palabras de 3+ caracteres
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        return None
    
    def _detect_query_type(self, query):
        """Detecta el tipo de consulta basado en palabras clave"""
        if any(word in query for word in ["busca", "información", "datos", "todo", "completo"]):
            return "search_comedor"
        elif any(word in query for word in ["compara", "diferencias", "vs", "versus", "cruce"]):
            return "compare_data"
        elif any(word in query for word in ["estadísticas", "conteo", "cuántos", "total", "promedio"]):
            return "statistics"
        elif any(word in query for word in ["análisis", "relación", "correlación", "tendencias"]):
            return "cross_analysis"
        else:
            return "general_search"
    
    def _search_comedor_info(self, comedor_name, original_query):
        """Busca información completa de un comedor específico"""
        if not comedor_name:
            return {
                "type": "error",
                "message": "No pude identificar el nombre del comedor. ¿Podrías especificarlo más claramente?"
            }
        
        results = {}
        total_records = 0
        
        # Buscar en todas las tablas
        for sheet_name, config in self.sheet_config.items():
            df = self.load_sheet_data(sheet_name)
            if df is not None and not df.empty:
                search_column = config["search_column"]
                if search_column in df.columns:
                    # Búsqueda flexible
                    mask = df[search_column].astype(str).str.contains(comedor_name, case=False, na=False)
                    matches = df[mask]
                    
                    if not matches.empty:
                        results[sheet_name] = {
                            "config": config,
                            "data": matches,
                            "count": len(matches)
                        }
                        total_records += len(matches)
        
        if total_records == 0:
            return {
                "type": "no_results",
                "message": f"No encontré información para el comedor '{comedor_name}'. ¿Verificaste el nombre?"
            }
        
        return {
            "type": "comedor_info",
            "comedor_name": comedor_name,
            "results": results,
            "total_records": total_records,
            "message": f"Encontré {total_records} registros para '{comedor_name}' en {len(results)} tabla(s)"
        }
    
    def _compare_comedor_data(self, comedor_name, query):
        """Compara datos entre diferentes tablas para un comedor"""
        info_result = self._search_comedor_info(comedor_name, query)
        
        if info_result["type"] != "comedor_info":
            return info_result
        
        comparison = {}
        results = info_result["results"]
        
        for sheet_name, sheet_data in results.items():
            config = sheet_data["config"]
            df = sheet_data["data"]
            
            # Extraer información clave para comparación
            comparison[sheet_name] = {
                "area": config["area"],
                "proposito": config["proposito"],
                "registros": len(df),
                "campos_unicos": list(df.columns),
                "primer_registro": df.iloc[0].to_dict() if len(df) > 0 else {}
            }
        
        return {
            "type": "comparison",
            "comedor_name": comedor_name,
            "comparison": comparison,
            "message": f"Análisis comparativo de '{comedor_name}' entre {len(comparison)} fuentes de datos"
        }
    
    def _generate_statistics(self, comedor_name, query):
        """Genera estadísticas generales o específicas"""
        stats = {}
        
        for sheet_name, config in self.sheet_config.items():
            df = self.load_sheet_data(sheet_name)
            if df is not None and not df.empty:
                search_column = config["search_column"]
                
                if comedor_name:
                    # Estadísticas específicas del comedor
                    mask = df[search_column].astype(str).str.contains(comedor_name, case=False, na=False)
                    filtered_df = df[mask]
                    stats[sheet_name] = {
                        "registros_comedor": len(filtered_df),
                        "total_registros": len(df),
                        "porcentaje": (len(filtered_df) / len(df) * 100) if len(df) > 0 else 0
                    }
                else:
                    # Estadísticas generales
                    stats[sheet_name] = {
                        "total_registros": len(df),
                        "comedores_unicos": df[search_column].nunique() if search_column in df.columns else 0,
                        "area": config["area"]
                    }
        
        return {
            "type": "statistics",
            "comedor_name": comedor_name,
            "stats": stats,
            "message": f"Estadísticas {'para ' + comedor_name if comedor_name else 'generales'}"
        }
    
    def _cross_analysis(self, comedor_name, query):
        """Realiza análisis cruzado entre diferentes fuentes"""
        if not comedor_name:
            return {
                "type": "error",
                "message": "Para análisis cruzado necesito el nombre específico del comedor"
            }
        
        # Buscar datos del comedor en todas las fuentes
        info_result = self._search_comedor_info(comedor_name, query)
        
        if info_result["type"] != "comedor_info":
            return info_result
        
        cross_data = {}
        results = info_result["results"]
        
        # Extraer campos comunes para análisis
        common_fields = ["direccion", "barrio", "comuna", "fecha", "telefono", "gestora"]
        
        for sheet_name, sheet_data in results.items():
            df = sheet_data["data"]
            config = sheet_data["config"]
            
            # Buscar campos similares
            matched_fields = {}
            for field in common_fields:
                for col in df.columns:
                    if field.lower() in col.lower():
                        if len(df) > 0:
                            matched_fields[field] = df[col].iloc[0]
                        break
            
            cross_data[sheet_name] = {
                "area": config["area"],
                "matched_fields": matched_fields,
                "total_fields": len(df.columns)
            }
        
        return {
            "type": "cross_analysis",
            "comedor_name": comedor_name,
            "cross_data": cross_data,
            "message": f"Análisis cruzado completado para '{comedor_name}'"
        }
    
    def _general_search(self, query):
        """Búsqueda general basada en la consulta"""
        return {
            "type": "general",
            "message": "Puedo ayudarte con consultas como:\n- 'Busca información del comedor Semillas'\n- 'Compara datos del comedor La Esperanza'\n- 'Estadísticas del comedor Nuevo Horizonte'\n- '¿Cuántos registros hay en total?'"
        }
def display_ai_response(response):
    """Muestra la respuesta del agente IA"""
    
    if response["type"] == "error" or response["type"] == "no_results":
        st.error(response["message"])
        
    elif response["type"] == "general":
        st.info(response["message"])
        
    elif response["type"] == "comedor_info":
        st.success(response["message"])
        
        # Mostrar información por pestañas
        if len(response["results"]) > 1:
            tabs = st.tabs([f"{config['config']['name']}" for config in response["results"].values()])
            
            for i, (sheet_name, sheet_data) in enumerate(response["results"].items()):
                with tabs[i]:
                    config = sheet_data["config"]
                    df = sheet_data["data"]
                    
                    st.markdown(f"**🏢 Área:** {config['area']}")
                    st.markdown(f"**🎯 Propósito:** {config['proposito']}")
                    if config['dashboard']:
                        st.markdown(f"**📈 Dashboard:** [{config['dashboard']}]({config['dashboard']})")
                    st.markdown(f"**📊 Registros encontrados:** {len(df)}")
                    
                    # Mostrar datos en tabla expandible
                    with st.expander(f"Ver {len(df)} registro(s)", expanded=False):
                        st.dataframe(df)
        else:
            # Solo una tabla con resultados
            sheet_name = list(response["results"].keys())[0]
            sheet_data = response["results"][sheet_name]
            config = sheet_data["config"]
            df = sheet_data["data"]
            
            st.markdown(f"**🏢 Área:** {config['area']}")
            st.markdown(f"**🎯 Propósito:** {config['proposito']}")
            if config['dashboard']:
                st.markdown(f"**📈 Dashboard:** [{config['dashboard']}]({config['dashboard']})")
            
            st.dataframe(df)
    
    elif response["type"] == "comparison":
        st.success(response["message"])
        
        comparison = response["comparison"]
        
        # Tabla de comparación
        comp_data = []
        for sheet_name, data in comparison.items():
            comp_data.append({
                "Tabla": sheet_name,
                "Área": data["area"],
                "Registros": data["registros"],
                "Total Campos": len(data["campos_unicos"])
            })
        
        st.dataframe(pd.DataFrame(comp_data))
        
        # Detalles por tabla
        for sheet_name, data in comparison.items():
            with st.expander(f"Detalles de {sheet_name}"):
                st.write(f"**Propósito:** {data['proposito']}")
                st.write(f"**Campos disponibles:** {', '.join(data['campos_unicos'][:10])}{'...' if len(data['campos_unicos']) > 10 else ''}")
    
    elif response["type"] == "statistics":
        st.success(response["message"])
        
        stats = response["stats"]
        
        # Crear visualización
        if response["comedor_name"]:
            # Estadísticas específicas del comedor
            data = []
            for sheet_name, stat in stats.items():
                data.append({
                    "Tabla": sheet_name,
                    "Registros del Comedor": stat["registros_comedor"],
                    "Total Registros": stat["total_registros"],
                    "Porcentaje": round(stat["porcentaje"], 2)
                })
            
            df_stats = pd.DataFrame(data)
            st.dataframe(df_stats)
            
            # Gráfico
            fig = px.bar(df_stats, x="Tabla", y="Registros del Comedor", 
                        title=f"Registros por tabla para {response['comedor_name']}")
            st.plotly_chart(fig)
        else:
            # Estadísticas generales
            data = []
            for sheet_name, stat in stats.items():
                data.append({
                    "Tabla": sheet_name,
                    "Área": stat["area"],
                    "Total Registros": stat["total_registros"],
                    "Comedores Únicos": stat["comedores_unicos"]
                })
            
            df_stats = pd.DataFrame(data)
            st.dataframe(df_stats)
            
            # Gráfico de registros por área
            fig = px.pie(df_stats, values="Total Registros", names="Área", 
                        title="Distribución de registros por área")
            st.plotly_chart(fig)
    
    elif response["type"] == "cross_analysis":
        st.success(response["message"])
        
        cross_data = response["cross_data"]
        
        # Mostrar análisis cruzado
        for sheet_name, data in cross_data.items():
            with st.expander(f"Datos en {sheet_name} ({data['area']})"):
                if data["matched_fields"]:
                    for field, value in data["matched_fields"].items():
                        st.write(f"**{field.title()}:** {value}")
                else:
                    st.write("No se encontraron campos comunes")

def show_ai_agent_page():
    """Muestra la página del agente IA"""
    
    st.title("🤖 Asistente IA de Comedores")
    st.markdown("---")
    
    st.markdown("""
    ### 💬 ¿En qué puedo ayudarte?
    
    Puedes hacerme preguntas como:
    - "Busca toda la información del comedor Semillas"
    - "Compara los datos del comedor La Esperanza entre todas las tablas"
    - "¿Cuántos registros tiene el comedor Nuevo Horizonte?"
    - "Análisis cruzado del comedor San José"
    - "Estadísticas generales de todos los comedores"
    """)
    
    # Inicializar el agente IA
    if 'ai_agent' not in st.session_state:
        st.session_state.ai_agent = ComedorAIAgent(SHEET_CONFIG, load_sheet_data)
    
    # Historial de conversación
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Campo de entrada de consulta
    user_query = st.text_input(
        "🔍 Escribe tu consulta:",
        placeholder="Ej: Busca información del comedor Semillas",
        key="ai_query_input"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        submit_query = st.button("🚀 Consultar", type="primary")
    
    with col2:
        if st.button("🗑️ Limpiar historial"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Procesar consulta
    if submit_query and user_query:
        with st.spinner("🧠 Procesando tu consulta..."):
            response = st.session_state.ai_agent.process_query(user_query)
            
            # Agregar al historial
            st.session_state.chat_history.append({
                "query": user_query,
                "response": response,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
    
    # Mostrar respuesta actual
    if st.session_state.chat_history:
        latest_interaction = st.session_state.chat_history[-1]
        
        st.markdown("### 💭 Respuesta:")
        display_ai_response(latest_interaction["response"])
    
    # Mostrar historial
    if len(st.session_state.chat_history) > 1:
        with st.expander("📚 Historial de conversación", expanded=False):
            for i, interaction in enumerate(reversed(st.session_state.chat_history[:-1])):
                st.markdown(f"**[{interaction['timestamp']}] 👤:** {interaction['query']}")
                st.markdown(f"**🤖:** {interaction['response']['message']}")
                if i < len(st.session_state.chat_history) - 2:
                    st.markdown("---")
    
    # Ejemplos de consultas
    st.markdown("### 💡 Ejemplos de consultas:")
    
    examples = [
        "Busca información del comedor Semillas",
        "Compara datos del comedor La Esperanza",
        "Estadísticas del comedor Nuevo Horizonte",
        "¿Cuántos comedores hay en total?",
        "Análisis cruzado del comedor San José"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state.ai_query_input = example
                st.rerun()

def show_search_page():
    """Muestra la página de búsqueda tradicional"""
    st.title("🍽️ Buscador de Comedores Comunitarios")
    st.markdown("---")
    
    # Sidebar para filtros
    with st.sidebar:
        st.header("🔍 Opciones de Búsqueda")
        
        # Tipo de búsqueda
        search_type = st.radio(
            "Tipo de búsqueda:",
            ["Búsqueda libre", "Seleccionar de lista"],
            index=0
        )
        
        if search_type == "Búsqueda libre":
            search_term = st.text_input(
                "Nombre del comedor:",
                placeholder="Escriba el nombre del comedor...",
                help="Puede escribir parte del nombre, la búsqueda es flexible"
            )
        else:
            with st.spinner("Cargando lista de comedores..."):
                comedores_list = get_all_comedores()
            
            search_term = st.selectbox(
                "Seleccione un comedor:",
                [""] + comedores_list,
                index=0,
                help="Seleccione de la lista completa de comedores"
            )
        
        # Filtro por tablas
        st.subheader("📊 Filtrar por tablas")
        selected_sheets = []
        
        for sheet_name, config in SHEET_CONFIG.items():
            if st.checkbox(config["name"], value=True, key=f"filter_{sheet_name}"):
                selected_sheets.append(sheet_name)
        
        if st.button("🔄 Actualizar datos", help="Forzar actualización desde Google Sheets"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ Cache limpiado. Los datos se actualizarán en la próxima búsqueda.")
            st.rerun()
    
    # Área principal
    if search_term and search_term.strip():
        st.markdown(f"### 🔍 Resultados para: '{search_term}'")
        
        total_results = 0
        results_by_sheet = {}
        
        # Buscar en cada tabla seleccionada
        with st.spinner("Buscando en las bases de datos..."):
            for sheet_name in selected_sheets:
                config = SHEET_CONFIG[sheet_name]
                df = load_sheet_data(sheet_name)
                
                if df is not None:
                    results = search_in_dataframe(df, config["search_column"], search_term)
                    if not results.empty:
                        results_by_sheet[sheet_name] = results
                        total_results += len(results)
        
        # Mostrar resumen de resultados
        if total_results > 0:
            st.success(f"✅ Se encontraron {total_results} registros en {len(results_by_sheet)} tabla(s)")
            
            # Tabs para cada tabla con resultados
            if len(results_by_sheet) > 1:
                tabs = st.tabs([SHEET_CONFIG[sheet]["name"] for sheet in results_by_sheet.keys()])
                
                for i, (sheet_name, results) in enumerate(results_by_sheet.items()):
                    with tabs[i]:
                        st.markdown(f"**{len(results)} registro(s) encontrado(s)**")
                        config = SHEET_CONFIG[sheet_name]
                        
                        for idx, record in results.iterrows():
                            display_record_card(record, sheet_name)
            else:
                # Solo una tabla con resultados
                sheet_name = list(results_by_sheet.keys())[0]
                results = results_by_sheet[sheet_name]
                config = SHEET_CONFIG[sheet_name]
                
                st.markdown(f"**{len(results)} registro(s) encontrado(s) en {config['name']}**")
                
                for idx, record in results.iterrows():
                    display_record_card(record, sheet_name)
        
        else:
            st.warning("❌ No se encontraron registros que coincidan con la búsqueda.")
            st.info("💡 Sugerencias:\n- Verifique la ortografía\n- Intente con parte del nombre\n- Seleccione más tablas para buscar")
    
    else:
        # Página de inicio
        st.markdown("""
        ## 👋 Bienvenido al Buscador de Comedores Comunitarios
        
        Esta aplicación te permite buscar información detallada sobre comedores comunitarios 
        en múltiples bases de datos.
        
        ### 📋 Bases de datos disponibles:
        """)
        
        for sheet_name, config in SHEET_CONFIG.items():
            with st.expander(f"{config['name']}", expanded=False):
                df = load_sheet_data(sheet_name)
                if df is not None:
                    st.write(f"📊 **Registros:** {len(df)}")
                    st.write(f"🏢 **Área:** {config['area']}")
                    st.write(f"🎯 **Propósito:** {config['proposito']}")
                    if config['dashboard']:
                        st.write(f"📈 **Dashboard:** [{config['dashboard']}]({config['dashboard']})")
                    st.write(f"🔍 **Campo de búsqueda:** `{config['search_column']}`")
        
        st.markdown("""
        ### 🚀 Cómo usar:
        1. **Escriba** el nombre del comedor en el campo de búsqueda (o seleccione de la lista)
        2. **Seleccione** las tablas donde desea buscar
        3. **Presione Enter** para iniciar la búsqueda
        4. **Explore** los resultados en tarjetas organizadas
        
        ### 💡 Consejos:
        - La búsqueda es **flexible**: puede escribir parte del nombre
        - Use el **selector de lista** para ver todos los comedores disponibles
        - **Filtre por tablas** para búsquedas más específicas
        - **Expanda las tarjetas** para ver información detallada
        """)

def main():
    # Banner superior con imagen - Configuración de tamaño y posición
    try:
        from PIL import Image
        banner_image = Image.open("imagenvjp.png")
        
        # CONFIGURACIÓN DE IMAGEN - Imagen centrada con tamaño controlado
        col1, col2, col3 = st.columns([1, 2, 1])  # Imagen ocupa 50% del ancho
        with col2:
            st.image(banner_image, use_container_width=True)
        
        # Espacio después de la imagen
        st.write("")  # Espacio pequeño después de la imagen
        
    except FileNotFoundError:
        st.error("❌ No se encontró la imagen 'imagenvjp.png' en el directorio del proyecto")
        st.info("💡 Asegúrate de que el archivo esté en la misma carpeta que la aplicación")
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar la imagen del banner: {str(e)}")
    
    # Menú de navegación
    page = st.sidebar.selectbox(
        "🧭 Navegación",
        ["🔍 Buscador", "🤖 Asistente IA"],
        index=0
    )
    
    if page == "🔍 Buscador":
        show_search_page()
    elif page == "🤖 Asistente IA":
        show_ai_agent_page()

if __name__ == "__main__":
    main()