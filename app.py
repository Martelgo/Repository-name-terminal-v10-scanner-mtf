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
        
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX"]
        
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

# --- 3. INTERFAZ ---
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
    st.subheader("Auditoría Individual de Activo")
    tk_audit = st.text_input("Ingrese Ticker para auditar:", "ORCL").upper()
    
    if tk_audit:
        with st.spinner(f"Auditando {tk_audit}..."):
            acc = yf.Ticker(tk_audit)
            info = acc.info
            hist = acc.history(period="1y")
            
            if not hist.empty:
                # --- Lógica de Auditoría V10 ---
                precio_act = acc.fast_info['last_price']
                target = info.get('targetMeanPrice', precio_act)
                margen_seg = ((target - precio_act) / precio_act) * 100
                ebitda_val = info.get('ebitda', 0)
                rsi_val = ta.rsi(hist['Close'], length=14).iloc[-1]
                sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                
                # Columnas de Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Precio Actual", f"${precio_act:.2f}")
                c2.metric("Precio Justo", f"${target:.2f}", f"{margen_seg:.1f}%")
                c3.metric("RSI (14d)", f"{rsi_val:.1f}")
                c4.metric("EBITDA", f"{ebitda_val:,.0f}")

                # Gráfico de Velas
                fig = go.Figure(data=[go.Candlestick(
                    x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                    name="Precio"
                )])
                # Añadir SMA 200 al gráfico
                hist['SMA200'] = hist['Close'].rolling(window=200).mean()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], name="SMA 200", line=dict(color='orange', width=2)))
                
                fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabla de Niveles V10
                st.write("### 📍 Niveles de Compra V10")
                n1, n2, n3 = precio_act*0.96, precio_act*0.92, precio_act*0.88
                st.table(pd.DataFrame({
                    "Nivel 1 (Entrada)": [f"${n1:.2f}"],
                    "Nivel 2 (Promedio)": [f"${n2:.2f}"],
                    "Nivel 3 (Suelo)": [f"${n3:.2f}"]
                }))
            else:
                st.error("No se pudieron obtener datos históricos para este ticker.")

with tab3:
    st.subheader("Sentimiento del Mercado (Termómetro)")
    spy = yf.Ticker("SPY").history(period="1mo")
    if not spy.empty:
        rsi_spy = ta.rsi(spy['Close'], length=14).iloc[-1]
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = rsi_spy,
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "white"},
                'steps': [
                    {'range': [0, 30], 'color': "red"},
                    {'range': [30, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "green"}]
            }
        ))
        fig_gauge.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)
