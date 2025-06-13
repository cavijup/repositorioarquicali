import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from datetime import datetime
import re
import os

# Configuración de la página
st.set_page_config(
    page_title="🍽️ Buscador de Comedores Comunitarios",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para cargar credenciales de Google Sheets
@st.cache_resource
def load_google_credentials():
    """Carga las credenciales de Google desde el archivo JSON"""
    try:
        credentials_path = 'google_credentials.json'
        if not os.path.exists(credentials_path):
            st.error("❌ No se encontró el archivo 'google_credentials.json'")
            st.info("💡 Asegúrate de que el archivo esté en el mismo directorio que la aplicación")
            return None
            
        # Usar directamente el archivo de credenciales
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scope)
        return credentials
        
    except FileNotFoundError:
        st.error("❌ No se encontró el archivo 'google_credentials.json'")
        st.info("💡 Asegúrate de que el archivo esté en el mismo directorio que la aplicación")
        return None
    except json.JSONDecodeError:
        st.error("❌ Error al leer el archivo 'google_credentials.json'. Verifica que sea un JSON válido")
        return None
    except Exception as e:
        st.error(f"❌ Error cargando credenciales: {str(e)}")
        return None

GOOGLE_SHEET_ID = "1svD6kfWvI9GTNzoqIhmSNa80MfGpjWqwQJRxOLxXOXI"

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

@st.cache_resource
def connect_to_google_sheets():
    """Conecta a Google Sheets y retorna el workbook"""
    try:
        # Cargar credenciales desde archivo JSON
        credentials = load_google_credentials()
        if credentials is None:
            return None
            
        # Autorizar cliente con gspread
        client = gspread.authorize(credentials)
        workbook = client.open_by_key(GOOGLE_SHEET_ID)
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

def main():
    # Banner superior con imagen - Configuración de tamaño y posición
    try:
        from PIL import Image
        banner_image = Image.open("imagenvjp.png")
        
        # Espacio superior (si quieres mover la imagen hacia abajo)
        # st.write("")  # Descomenta para agregar espacio arriba
        
        # CONFIGURACIÓN DE IMAGEN - Elige una de las siguientes opciones:
        
        # OPCIÓN 1: Imagen centrada con tamaño controlado (RECOMENDADA)
        col1, col2, col3 = st.columns([1, 2, 1])  # Imagen ocupa 50% del ancho
        with col2:
            st.image(banner_image, use_container_width=True)
        
        # OPCIÓN 2: Imagen con ancho fijo (descomenta para usar)
        # st.image(banner_image, width=500)  # Cambia 500 por el ancho deseado
        
        # OPCIÓN 3: Imagen más estrecha y centrada (descomenta para usar)
        # col1, col2, col3 = st.columns([2, 1, 2])  # Imagen ocupa 25% del ancho
        # with col2:
        #     st.image(banner_image, use_container_width=True)
        
        # OPCIÓN 4: Imagen con CSS personalizado (descomenta para usar)
        # st.markdown("""
        # <style>
        # .banner-container {
        #     display: flex;
        #     justify-content: center;
        #     margin-top: 10px;
        #     margin-bottom: 20px;
        # }
        # .banner-container img {
        #     max-width: 400px;
        #     height: auto;
        #     border-radius: 10px;
        #     box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        # }
        # </style>
        # """, unsafe_allow_html=True)
        # st.markdown('<div class="banner-container">', unsafe_allow_html=True)
        # st.image(banner_image, use_container_width=True)
        # st.markdown('</div>', unsafe_allow_html=True)
        
        # Espacio después de la imagen
        st.write("")  # Espacio pequeño después de la imagen
        # st.markdown("<br>", unsafe_allow_html=True)  # Descomenta para más espacio
        
    except FileNotFoundError:
        st.error("❌ No se encontró la imagen 'imagenvjp.png' en el directorio del proyecto")
        st.info("💡 Asegúrate de que el archivo 'imagenvjp.png' esté en la misma carpeta que la aplicación")
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar la imagen del banner: {str(e)}")
    
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

if __name__ == "__main__":
    main()