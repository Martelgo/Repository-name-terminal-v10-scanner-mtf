import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Configuración visual
st.set_page_config(page_title="V10 Elite Terminal", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Autónomo")

# --- FUNCIONES DE EXTRACCIÓN AUTOMÁTICA ---
@st.cache_data(ttl=86400) # La lista de empresas solo cambia rara vez, se guarda 24h
def obtener_universo_autonomo():
    try:
        # Extraer S&P 500 de Wikipedia
        sp500_table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        # Extraer NASDAQ 100 de Wikipedia
        nasdaq_table = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        
        # Lista BMV (Principales por liquidez para evitar errores de data)
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
                       "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX"]
        
        return {
            "S&P 500": sp500_tickers,
            "NASDAQ 100": nasdaq_tickers,
            "BMV (México)": bmv_tickers
        }
    except Exception as e:
        st.error(f"Error al conectar con las fuentes de índices: {e}")
        return {"Error": []}

@st.cache_data(ttl=3600) # El análisis de precios se guarda 1 hora
def ejecutar_escaneo_v10(lista_tickers):
    resultados = []
    progreso = st.progress(0)
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            ticker = yf.Ticker(t)
            # Usamos fast_info para que el escaneo de 600+ activos no tarde horas
            p = ticker.fast_info['last_price']
            info = ticker.info
            
            # Lógica Fundamental V10
            tj = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
            ebitda = info.get('ebitda', 0) or 0
            m = ((tj - p) / p) * 100 if p else 0
            
            # FILTRO ESTRICTO: Solo Compra o Vigilar
            if m > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
            elif m > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue # DESCARTAR AUTOMÁTICAMENTE
                
            resultados.append({
                "Ticker": t,
                "Estado": estado,
                "Precio": round(p, 2),
                "Margen %": round(m, 1),
                "Sector": info.get('sector', 'N/A')
            })
        except:
            continue
        progreso.progress((i + 1) / total)
    
    return pd.DataFrame(resultados)

# --- NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR (AUTÓNOMO) ---
with tab1:
    st.subheader("Radar de Oportunidades Filtradas")
    mercado_selec = st.selectbox("Selecciona el Mercado a Analizar:", ["S&P 500", "NASDAQ 100", "BMV (México)"])
    
    if st.button(f"🚀 Iniciar Escaneo Autónomo de {mercado_selec}"):
        universo = obtener_universo_autonomo()
        lista_activos = universo.get(mercado_selec, [])
        
        if lista_activos:
            st.info(f"Escaneando {len(lista_activos)} activos de {mercado_selec}. Por favor, espera...")
            df_resultados = ejecutar_escaneo_v10(lista_activos)
            
            if not df_resultados.empty:
                st.success(f"Escaneo completado. Se encontraron {len(df_resultados)} oportunidades.")
                st.dataframe(df_resultados.sort_values(by="Margen %", ascending=False), use_container_width=True)
            else:
                st.warning("No se encontraron activos que cumplan con los criterios de Compra o Vigilar.")
    
    st.caption("Nota: El escaneo procesa cientos de activos. Puede tardar de 2 a 5 minutos dependiendo de la conexión.")

# --- Módulos de Auditoría y Sentimiento se mantienen abajo con tu lógica original ---
