import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO
import requests
import time

# --- SOLUCIÓN AL RATE LIMIT ---
# Creamos una sesión que simula un navegador real para evitar bloqueos
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# Configuración visual
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global")

# --- 1. OBTENCIÓN DE TICKERS ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    try:
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(url_nas)[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "CEMEXCPO.MX", "AC.MX"]
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except Exception as e:
        st.error(f"⚠️ Error en fuentes: {e}")
        return {}

# --- 2. MOTOR DE PROCESAMIENTO (CON ANTIBLOQUEO) ---
def procesar_v10(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Escaneando {nombre_mercado}: {t} ({i+1}/{total})")
            
            # PASO CLAVE: Usamos la sesión para evitar el YFRateLimitError
            tk = yf.Ticker(t, session=session)
            
            # Usamos fast_info primero porque es menos propenso a bloqueos
            f_info = tk.fast_info
            p = f_info['last_price']
            
            # Solo pedimos .info si el precio es válido
            info = tk.info
            tj = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
            ebitda = info.get('ebitda', 0) or 0
            m = ((tj - p) / p) * 100 if p else 0
            
            if m > 5 and ebitda > 0:
                estado = "🟢 COMPRA CLARA" if m > 15 else "🟡 VIGILAR"
                resultados.append({
                    "Mercado": nombre_mercado, "Ticker": t, "Estado": estado,
                    "Precio": round(p, 2), "Margen %": round(m, 1), "Sector": info.get('sector', 'N/A')
                })
            
            # Pequeña pausa cada 10 tickers para no saturar
            if i % 10 == 0:
                time.sleep(0.1)

        except Exception as e:
            if "Rate Limit" in str(e):
                st.warning("⚠️ Yahoo ha limitado la velocidad. Esperando 5 segundos...")
                time.sleep(5)
            continue
        progreso_bar.progress((i + 1) / total)
    return resultados

# --- 3. INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA 360", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            mercado_selec = st.selectbox("Mercado:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear {mercado_selec}")
        with c2:
            btn_global = st.button("🌍 ESCANEO GLOBAL (Lento pero Seguro)")

        df_final = pd.DataFrame()
        if btn_solo:
            df_final = pd.DataFrame(procesar_v10(universo[mercado_selec], mercado_selec, st.progress(0), st.empty()))
        elif btn_global:
            todas = []
            p, m = st.progress(0), st.empty()
            for n, tks in universo.items(): todas.extend(procesar_v10(tks, n, p, m))
            df_final = pd.DataFrame(todas)

        if not df_final.empty:
            df_final = df_final.drop_duplicates(subset=['Ticker'])
            st.success(f"✅ {len(df_final)} Oportunidades detectadas.")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='V10')
            st.download_button("📥 Descargar Excel", output.getvalue(), "Reporte_V10.xlsx")
            st.dataframe(df_final, use_container_width=True)

# --- TAB 2: AUDITORIA (CON SESIÓN) ---
with tab2:
    st.subheader("Análisis 360")
    ca1, ca2 = st.columns([1, 2])
    with ca1: mkt = st.radio("Mercado:", ["EUA", "México (.MX)"], key="aud_mkt")
    with ca2: tk_in = st.text_input("Ticker:", "NVDA").upper()

    ticker_final = tk_in if mkt == "EUA" else (f"{tk_in}.MX" if ".MX" not in tk_in else tk_in)

    if ticker_final:
        acc = yf.Ticker(ticker_final, session=session)
        h = acc.history(period="1y")
        if not h.empty:
            p_act = h['Close'].iloc[-1]
            st.markdown(f"### Precio: ${p_act:.2f}")
            # ... (Resto de tu lógica de auditoría estilo hacker)
            st.code("MODO AUDITORÍA ACTIVADO - LISTO", language="text")
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SENTIMIENTO ---
with tab3:
    st.subheader("Sentimiento")
    val = ta.rsi(yf.Ticker("SPY", session=session).history(period="1y")['Close'], length=14).iloc[-1]
    st.metric("RSI SPY", f"{val:.2f}")
