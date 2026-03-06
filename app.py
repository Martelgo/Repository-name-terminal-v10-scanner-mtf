import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO
import time

# Configuración visual
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner de Alta Disponibilidad")

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
        
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "CEMEXCPO.MX", "AC.MX"]
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except Exception as e:
        st.error(f"⚠️ Error en fuentes: {e}")
        return {}

# --- 2. MOTOR DE PROCESAMIENTO (CON PAUSA ANTI-BLOQUEO) ---
def procesar_v10(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            
            # 1. Intentamos obtener precio rápido
            p = tk.fast_info['last_price']
            
            # 2. Intentamos fundamentales
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
            
            # --- PAUSA CRÍTICA ---
            # Yahoo permite aprox 2000 peticiones por hora. 
            # 0.5 seg asegura que no excedamos el límite de ráfaga.
            time.sleep(0.5)

        except Exception as e:
            if "Rate Limit" in str(e) or "429" in str(e):
                monitor_text.warning(f"⚠️ Límite alcanzado en {t}. Esperando 10 segundos...")
                time.sleep(10)
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
            mercado_selec = st.selectbox("Seleccionar Mercado:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear {mercado_selec}")
        with c2:
            st.write("Análisis Global")
            btn_global = st.button("🌍 EJECUTAR ESCANEO TOTAL")

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
            st.download_button(label="📥 Descargar Excel", data=output.getvalue(), file_name='Reporte_V10.xlsx')
            
            df_final.index = range(1, len(df_final) + 1)
            st.dataframe(df_final.sort_values(by=["Mercado", "Margen %"], ascending=[True, False]), use_container_width=True)

with tab2:
    st.subheader("Análisis 360")
    ca1, ca2 = st.columns([1, 2])
    with ca1: mkt = st.radio("Mercado:", ["EUA", "México (.MX)"], key="aud_mkt")
    with ca2: tk_in = st.text_input("Ticker:", "MSFT").upper()

    ticker_final = tk_in if mkt == "EUA" else (f"{tk_in}.MX" if ".MX" not in tk_in else tk_in)

    if ticker_final:
        with st.spinner('Ejecutando Auditoría...'):
            acc = yf.Ticker(ticker_final)
            h = acc.history(period="1y")
            if not h.empty:
                info = acc.info
                p_act = h['Close'].iloc[-1]
                st.markdown(f"### 🏢 {info.get('longName', ticker_final)}")
                
                # Consola Hacker
                reporte = f"""
=================================================================
                  MÉTRICA           VALOR       ESTADO
-----------------------------------------------------------------
            Precio Actual          ${p_act:>8.2f}    Cotizando
                   EBITDA          {info.get('ebitda', 0):>14,}       {"✅" if info.get('ebitda', 0) > 0 else "⚠️"}
=================================================================
"""
                st.code(reporte, language="text")
                fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
                fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Indicador de Pánico y Codicia")
    spy_h = yf.Ticker("SPY").history(period="1y")
    val = ta.rsi(spy_h['Close'], length=14).iloc[-1]
    
    fig_sent = go.Figure(go.Indicator(
        mode = "gauge+number", value = val,
        title = {'text': "Sentimiento RSI (SPY)", 'font': {'size': 18}},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "lightgray"},
                 'steps': [{'range': [0, 30], 'color': "red"}, 
                           {'range': [30, 70], 'color': "gray"}, 
                           {'range': [70, 100], 'color': "green"}]}
    ))
    fig_sent.update_layout(height=350, template="plotly_dark")
    st.plotly_chart(fig_sent, use_container_width=True)
