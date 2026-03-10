import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO
import requests

# Configuración visual de la Terminal
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global Autónomo")

# --- CONFIGURACIÓN TELEGRAM ---
st.sidebar.header("🤖 Configuración Bot Telegram")
tel_token = st.sidebar.text_input("Bot Token:", type="password")
tel_chatid = st.sidebar.text_input("Chat ID:")

def enviar_telegram(mensaje):
    if tel_token and tel_chatid:
        url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
        payload = {"chat_id": tel_chatid, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            st.error(f"Error enviando Telegram: {e}")

# --- 1. OBTENCIÓN DE TICKERS ---
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
        
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX"]
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return {}

# --- 2. MOTOR DE PROCESAMIENTO ---
def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            p = tk.fast_info['last_price']
            info = tk.info
            
            p_justo = info.get('targetMeanPrice', p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            ebitda = info.get('ebitda', 0) or 0
            
            n1 = round(p * 0.96, 2)
            
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
                if p <= n1:
                    enviar_telegram(f"🚨 *V10 COMPRA:* {t}\nPrecio: ${p:.2f}\nMargen: {margen:.1f}%")
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else: continue
                
            resultados.append({"Mercado": nombre_mercado, "Ticker": t, "Estado": estado, 
                               "Precio": round(p, 2), "Margen %": round(margen, 1), "Nivel 1": n1})
        except: continue
        progreso_bar.progress((i + 1) / total)
    return resultados

# --- 3. INTERFAZ RECONSTRUIDA ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    if universo:
        col1, col2 = st.columns(2)
        with col1:
            m_sel = st.selectbox("Mercado:", list(universo.keys()))
            btn_s = st.button(f"🚀 Escanear {m_sel}")
        with col2:
            btn_g = st.button("🌍 ESCANEO GLOBAL")

        df_final = pd.DataFrame()
        if btn_s or btn_g:
            prog = st.progress(0); mon = st.empty()
            if btn_s: 
                df_final = pd.DataFrame(procesar_lista_tickers(universo[m_sel], m_sel, prog, mon))
            else:
                todas = []
                for k, v in universo.items(): todas.extend(procesar_lista_tickers(v, k, prog, mon))
                df_final = pd.DataFrame(todas)
            mon.empty()

        if not df_final.empty:
            st.dataframe(df_final.sort_values(by="Margen %", ascending=False), use_container_width=True)

with tab2:
    st.subheader("Auditoría de Activo Individual")
    tk_in = st.text_input("Ingresa Ticker (ej: TSLA, ORCL):", "TSLA").upper()
    if tk_in:
        asset = yf.Ticker(tk_in)
        hist = asset.history(period="1y")
        if not hist.empty:
            # Gráfica de Velas Restaurada
            fig_cand = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
            fig_cand.update_layout(template="plotly_dark", title=f"Histórico 1 Año: {tk_in}", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_cand, use_container_width=True)
        else:
            st.warning("No se encontraron datos para este ticker.")

with tab3:
    st.subheader("Sentimiento del Mercado (Termómetro)")
    spy = yf.Ticker("SPY").history(period="1mo")
    if not spy.empty:
        rsi_spy = ta.rsi(spy['Close'], length=14).iloc[-1]
        
        # Restauración del Velocímetro
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = rsi_spy,
            title = {'text': "RSI SPY (Sentimiento)"},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "white"},
                'steps': [
                    {'range': [0, 30], 'color': "red"},
                    {'range': [30, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "green"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': rsi_spy}
            }
        ))
        fig_gauge.update_layout(template="plotly_dark")
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.info("RSI < 30: Pánico (Oportunidad) | RSI > 70: Euforia (Riesgo)")
