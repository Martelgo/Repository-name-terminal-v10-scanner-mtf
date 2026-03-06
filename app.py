import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO

# Configuración visual de la Terminal V10
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global Autónomo")

# --- 1. OBTENCIÓN AUTOMÁTICA DE TICKERS (WIKIPEDIA FIX) ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        # S&P 500
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp, storage_options=headers)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        # NASDAQ 100
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(url_nas, storage_options=headers)[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        
        # BMV (Principales por liquidez)
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
                       "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX"]
        
        return {
            "S&P 500": sp500_tickers,
            "NASDAQ 100": nasdaq_tickers,
            "BMV (México)": bmv_tickers
        }
    except Exception as e:
        st.error(f"⚠️ Error al conectar con fuentes de mercados: {e}")
        return {}

# --- 2. MOTOR DE ESCANEO PRO (INDIVIDUAL Y GLOBAL) ---
def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            
            # Datos fundamentales y de precio
            p = tk.fast_info['last_price']
            info = tk.info
            
            # Lógica de Valoración V10
            target = info.get('targetMeanPrice')
            eps = info.get('forwardEps')
            pe = info.get('forwardPE', 15)
            ebitda = info.get('ebitda', 0) or 0
            
            # Fallback de precio justo
            p_justo = target if target else (pe * eps if eps else p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            
            # FILTRO ESTRICTO V10: Solo Compra Clara o Vigilar
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue 
                
            resultados.append({
                "Mercado": nombre_mercado,
                "Ticker": t,
                "Estado": estado,
                "Precio": round(p, 2),
                "Margen %": round(margen, 1),
                "Sector": info.get('sector', 'N/A')
            })
        except:
            continue
        progreso_bar.progress((i + 1) / total)
    
    return resultados

# --- 3. INTERFAZ DE NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR ---
with tab1:
    st.subheader("Radar de Oportunidades Segmentado")
    universo = obtener_universo_autonomo()
    
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            mercado_selec = st.selectbox("Seleccionar Mercado Específico:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear solo {mercado_selec}")
        with c2:
            st.write("Análisis Total (S&P + NASDAQ + BMV)")
            btn_global = st.button("🌍 EJECUTAR ESCANEO GLOBAL")

        df_final = pd.DataFrame()

        # Lógica de ejecución
        if btn_solo:
            progreso = st.progress(0)
            monitor = st.empty()
            datos = procesar_lista_tickers(universo[mercado_selec], mercado_selec, progreso, monitor)
            df_final = pd.DataFrame(datos)
            monitor.empty()

        elif btn_global:
            todas_oportunidades = []
            progreso = st.progress(0)
            monitor = st.empty()
            
            for m_nombre, m_tickers in universo.items():
                res_m = procesar_lista_tickers(m_tickers, m_nombre, progreso, monitor)
                todas_oportunidades.extend(res_m)
            
            df_final = pd.DataFrame(todas_oportunidades)
            monitor.empty()

        # Mostrar Resultados y Descarga
        if not df_final.empty:
            st.success(f"✅ Análisis completado: {len(df_final)} oportunidades detectadas.")
            
            # Generar Excel en memoria
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Oportunidades_V10')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Descargar Reporte en Excel",
                data=excel_data,
                file_name='Reporte_V10_Oportunidades.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # Tabla con numeración
            df_final.index = range(1, len(df_final) + 1)
            st.dataframe(df_final.sort_values(by=["Mercado", "Margen %"], ascending=[True, False]), use_container_width=True)
        elif btn_solo or btn_global:
            st.warning("No se encontraron activos que cumplan con los filtros de Compra o Vigilar.")

# --- TAB 2: AUDITORIA ---
with tab2:
    st.subheader("Análisis 360 de Activo")
    tk_in = st.text_input("Ingresa Ticker (ej: NVDA o WALMEX.MX):", "MSFT").upper()
    if tk_in:
        acc = yf.Ticker(tk_in)
        h = acc.history(period="1y")
        if not h.empty:
            st.markdown(f"### Análisis de {tk_in}")
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SENTIMIENTO ---
with tab3:
    st.subheader("Indicador de Pánico y Codicia")
    spy = yf.Ticker("SPY").history(period="1mo")
    rsi_spy = ta.rsi(spy['Close'], length=14).iloc[-1]
    st.metric("RSI S&P 500 (SPY)", f"{rsi_spy:.2f}")
    if rsi_spy < 35: st.error("🔥 MIEDO EXTREMO - Oportunidad de Compra")
    elif rsi_spy > 65: st.warning("⚠️ EUFORIA - Cautela")
    else: st.info("⚖️ MERCADO NEUTRAL")
