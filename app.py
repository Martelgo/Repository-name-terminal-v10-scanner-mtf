import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO

# 1. CONFIGURACIÓN VISUAL
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global Autónomo")

# --- 2. OBTENCIÓN DE TICKERS (VERSIÓN RESILIENTE) ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    respaldo = {
        "S&P 500": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
        "NASDAQ 100": ["AMD", "TSM", "ASML", "AVGO", "INTC", "QCOM"],
        "BMV (México)": ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "CEMEXCPO.MX"]
    }
    try:
        # S&P 500
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_tickers = pd.read_html(url_sp, storage_options=headers)[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        
        # NASDAQ 100
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_tickers = pd.read_html(url_nas, storage_options=headers)[4]['Ticker'].str.replace('.', '-', regex=False).tolist()
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": respaldo["BMV (México)"]}
    except:
        return respaldo

# --- 3. GESTIÓN DE MEMORIA (SESSION STATE) ---
if 'df_radar' not in st.session_state:
    st.session_state.df_radar = pd.DataFrame()

# --- 4. MOTOR DE PROCESAMIENTO ---
def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            # Usamos fast_info para no saturar
            p = tk.fast_info['last_price']
            info = tk.info
            
            target = info.get('targetMeanPrice')
            eps = info.get('forwardEps')
            pe = info.get('forwardPE', 15)
            ebitda = info.get('ebitda', 0) or 0
            
            p_justo = target if target else (pe * eps if eps else p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            
            if margen > 15 and ebitda > 0: estado = "🟢 COMPRA CLARA"
            elif margen > 5 and ebitda > 0: estado = "🟡 VIGILAR"
            else: continue 
                
            resultados.append({
                "Mercado": nombre_mercado, "Ticker": t, "Estado": estado,
                "Precio": round(p, 2), "Margen %": round(margen, 1),
                "Sector": info.get('sector', 'N/A')
            })
        except: continue
        progreso_bar.progress((i + 1) / total)
    return resultados

# --- 5. INTERFAZ POR PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    
    c1, c2 = st.columns(2)
    with c1:
        mercado_selec = st.selectbox("Selecciona Mercado:", list(universo.keys()))
        btn_solo = st.button(f"🚀 Escanear {mercado_selec}", use_container_width=True)
    with c2:
        st.write("Análisis Completo")
        btn_global = st.button("🌍 EJECUTAR ESCANEO GLOBAL", use_container_width=True)

    if btn_solo or btn_global:
        progreso = st.progress(0)
        monitor = st.empty()
        if btn_solo:
            datos = procesar_lista_tickers(universo[mercado_selec], mercado_selec, progreso, monitor)
            st.session_state.df_radar = pd.DataFrame(datos)
        else:
            todas = []
            for m_nombre, m_tickers in universo.items():
                res = procesar_lista_tickers(m_tickers, m_nombre, progreso, monitor)
                todas.extend(res)
            st.session_state.df_radar = pd.DataFrame(todas)
        monitor.empty()
        st.rerun()

    if not st.session_state.df_radar.empty:
        df_f = st.session_state.df_radar.drop_duplicates(subset=['Ticker'])
        st.success(f"✅ {len(df_f)} Oportunidades encontradas.")
        
        # Excel Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_f.to_excel(writer, index=False, sheet_name='V10_Radar')
        st.download_button("📥 Descargar Reporte Excel", output.getvalue(), "Reporte_V10.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        st.dataframe(df_f.sort_values(by="Margen %", ascending=False), use_container_width=True)

with tab2:
    st.subheader("Auditoría 360")
    tk_in = st.text_input("Ticker:", "MSFT").upper()
    if st.button("🔍 Auditar Activo"):
        acc = yf.Ticker(tk_in)
        h = acc.history(period="1y")
        if not h.empty:
            p_act = h['Close'].iloc[-1]
            st.metric(f"Precio Actual {tk_in}", f"${p_act:.2f}")
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Sentimiento de Mercado")
    if st.button("🌡️ Medir Pulso Global"):
        spy = yf.Ticker("SPY").history(period="1y")
        val = ta.rsi(spy['Close'], length=14).iloc[-1]
        
        col_gauge = "red" if val < 30 else ("green" if val > 70 else "gray")
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = val,
            title = {'text': "RSI SPY (Pánico/Codicia)"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': col_gauge},
                     'steps': [{'range': [0, 30], 'color': "red"}, {'range': [70, 100], 'color': "green"}]}
        ))
        fig_g.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_g, use_container_width=True)

