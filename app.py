import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO

# Configuración visual
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Consola de Auditoría")

# --- (Las funciones obtener_universo_autonomo y procesar_lista_tickers se mantienen igual) ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp, storage_options=headers)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(url_nas, storage_options=headers)[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "GAPB.MX", "CEMEXCPO.MX", "BIMBOA.MX", "GRUMAB.MX", "KIMBERA.MX"]
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except: return {}

def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            p = tk.fast_info['last_price']
            info = tk.info
            tj = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
            ebitda = info.get('ebitda', 0) or 0
            m = ((tj - p) / p) * 100 if p else 0
            if m > 5 and ebitda > 0:
                estado = "🟢 COMPRA CLARA" if m > 15 else "🟡 VIGILAR"
                resultados.append({"Mercado": nombre_mercado, "Ticker": t, "Estado": estado, "Precio": round(p, 2), "Margen %": round(m, 1), "Sector": info.get('sector', 'N/A')})
        except: continue
        progreso_bar.progress((i + 1) / total)
    return resultados

# --- NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA PRO", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR (Se mantiene tu lógica de escaneo) ---
with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            m_sel = st.selectbox("Mercado:", list(universo.keys()))
            b_s = st.button(f"🚀 Escanear {m_sel}")
        with c2: b_g = st.button("🌍 ESCANEO GLOBAL")
        
        df_f = pd.DataFrame()
        if b_s: df_f = pd.DataFrame(procesar_lista_tickers(universo[m_sel], m_sel, st.progress(0), st.empty()))
        elif b_g:
            todo = []
            p = st.progress(0)
            m = st.empty()
            for n, tks in universo.items(): todo.extend(procesar_lista_tickers(tks, n, p, m))
            df_f = pd.DataFrame(todo)
        
        if not df_f.empty:
            df_f = df_f.drop_duplicates(subset=['Ticker'])
            st.dataframe(df_f.sort_values(by="Margen %", ascending=False), use_container_width=True)

# --- TAB 2: AUDITORIA PRO (RESTAURADA Y MEJORADA) ---
with tab2:
    st.subheader("Consola de Auditoría Profunda")
    col_search1, col_search2 = st.columns([1, 3])
    with col_search1:
        ticker_input = st.text_input("Ingresa Ticker:", "NVDA").upper()
    
    if ticker_input:
        with st.spinner(f'Auditando {ticker_input}...'):
            asset = yf.Ticker(ticker_input)
            hist = asset.history(period="1y")
            info = asset.info
            
            if not hist.empty:
                # Cálculos Técnicos
                hist['RSI'] = ta.rsi(hist['Close'], length=14)
                hist['SMA200'] = ta.sma(hist['Close'], length=200)
                
                # Datos actuales
                p_act = hist['Close'].iloc[-1]
                rsi_v = hist['RSI'].iloc[-1]
                sma_v = hist['SMA200'].iloc[-1]
                
                # Fundamentales
                p_target = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
                margen_seg = ((p_target - p_act) / p_act) * 100
                ebitda_v = info.get('ebitda', "N/A")

                # --- DISEÑO DE MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Precio Actual", f"${p_act:.2f}")
                m2.metric("Precio Justo (V10)", f"${p_target:.2f}", f"{margen_seg:.1f}%")
                m3.metric("RSI (14d)", f"{rsi_v:.1f}", "Sobreventa" if rsi_v < 30 else "Normal")
                m4.metric("Tendencia (SMA 200)", f"${sma_v:.2f}", "ALCISTA" if p_act > sma_v else "BAJISTA")

                # --- GRÁFICO PROFESIONAL ---
                
                fig = go.Figure()
                # Velas
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Precio"))
                # SMA 200
                fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='yellow', width=1.5), name="SMA 200"))
                
                fig.update_layout(title=f"Gráfico Histórico: {info.get('longName', ticker_input)}", template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
                st.plotly_chart(fig, use_container_width=True)

                # Resumen de Empresa
                with st.expander("Ver Descripción de la Empresa"):
                    st.write(info.get('longBusinessSummary', 'No hay descripción disponible.'))
            else:
                st.error("No se encontraron datos para este Ticker. Revisa si está bien escrito.")

# --- TAB 3: SENTIMIENTO ---
with tab3:
    st.subheader("Sentimiento del Mercado")
    spy_rsi = ta.rsi(yf.Ticker("SPY").history(period="1mo")['Close'], length=14).iloc[-1]
    st.metric("RSI SPY", f"{spy_rsi:.2f}")
