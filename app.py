import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO

# Configuración visual de la App
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global")

# --- 1. OBTENCIÓN AUTOMÁTICA DE TICKERS ---
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
        
        # BMV
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
                       "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX",
                       "ALFAA.MX", "BIMBOA.MX", "GRUMAB.MX", "KIMBERA.MX", "AC.MX"]
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except Exception as e:
        st.error(f"⚠️ Error en fuentes: {e}")
        return {}

# --- 2. MOTOR DE ESCANEO ---
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
                resultados.append({
                    "Mercado": nombre_mercado, "Ticker": t, "Estado": estado,
                    "Precio": round(p, 2), "Margen %": round(m, 1), "Sector": info.get('sector', 'N/A')
                })
        except: continue
        progreso_bar.progress((i + 1) / total)
    return resultados

# --- NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA 360", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR (TU MOTOR POTENTE) ---
with tab1:
    st.subheader("Radar de Oportunidades Segmentado")
    universo = obtener_universo_autonomo()
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            mercado_selec = st.selectbox("Mercado Específico:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear {mercado_selec}")
        with c2:
            btn_global = st.button("🌍 EJECUTAR ESCANEO GLOBAL")

        df_final = pd.DataFrame()
        if btn_solo:
            df_final = pd.DataFrame(procesar_lista_tickers(universo[mercado_selec], mercado_selec, st.progress(0), st.empty()))
        elif btn_global:
            todas = []
            p, m = st.progress(0), st.empty()
            for n, tks in universo.items(): todas.extend(procesar_lista_tickers(tks, n, p, m))
            df_final = pd.DataFrame(todas)

        if not df_final.empty:
            df_final = df_final.drop_duplicates(subset=['Ticker'])
            st.success(f"✅ {len(df_final)} Oportunidades detectadas")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='V10_Report')
            st.download_button(label="📥 Descargar Reporte en Excel", data=output.getvalue(), file_name='Reporte_V10.xlsx')
            
            df_final.index = range(1, len(df_final) + 1)
            st.dataframe(df_final.sort_values(by=["Mercado", "Margen %"], ascending=[True, False]), use_container_width=True)

# --- TAB 2: AUDITORIA (CONSOLA ORIGINAL RESTAURADA) ---
with tab2:
    st.subheader("Análisis 360 de Activo")
    c_i1, c_i2 = st.columns([1, 2])
    with c_i1: mkt = st.radio("Mercado:", ["EUA", "México (.MX)"])
    with c_i2: tk_in = st.text_input("Ticker:", "MSFT").upper()

    ticker_final = tk_in if mkt == "EUA" else (f"{tk_in}.MX" if ".MX" not in tk_in else tk_in)

    if ticker_final:
        with st.spinner('Auditando...'):
            acc = yf.Ticker(ticker_final)
            h = acc.history(period="1y")
            info = acc.info
            if not h.empty:
                h['RSI'] = ta.rsi(h['Close'], length=14)
                h['SMA200'] = ta.sma(h['Close'], length=200)
                p_act = h['Close'].iloc[-1]
                rsi_v = h['RSI'].iloc[-1] if not pd.isna(h['RSI'].iloc[-1]) else 50
                sma_v = h['SMA200'].iloc[-1] if not pd.isna(h['SMA200'].iloc[-1]) else p_act
                p_justo = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
                margen = ((p_justo - p_act) / p_act) * 100
                ebitda = info.get('ebitda', 0) or 0
                
                est_m = "DESCUENTO" if margen > 15 else "CARO"
                est_r = "SOBREVENTA" if rsi_v < 35 else ("SOBRECOMPRA" if rsi_v > 65 else "NEUTRAL")
                est_t = "ALCISTA" if p_act > sma_v else "BAJISTA"
                est_e = "Sólido" if ebitda > 0 else "RIESGO"

                st.markdown(f"### 🏢 {info.get('longName', ticker_final)}")
                reporte_v2 = f"""
=================================================================
                  MÉTRICA           VALOR       ESTADO
-----------------------------------------------------------------
            Precio Actual          ${p_act:>8.2f}    Cotizando
Precio Justo de la Acción          ${p_justo:>8.2f}    Referencia
              Margen Seg.            {margen:>7.1f}%       {"✅" if est_m=="DESCUENTO" else "❌"} {est_m}
                RSI (14d)             {rsi_v:>7.1f}  {"📉" if rsi_v<35 else "⚖️"} {est_r}
                  SMA 200          ${sma_v:>8.2f}    {"🚀" if est_t=="ALCISTA" else "⚠️"} {est_t}
                   EBITDA          {ebitda:>14,}       {"✅" if ebitda > 0 else "⚠️"} {est_e}
-----------------------------------------------------------------
📍 NIVELES DE COMPRA:  1: ${p_act*0.96:.2f} | 2: ${p_act*0.92:.2f} | 3: ${p_act*0.88:.2f}
=================================================================
"""
                st.code(reporte_v2, language="text")
                fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
                fig.add_trace(go.Scatter(x=h.index, y=h['SMA200'], line=dict(color='orange', width=2), name="SMA 200"))
                fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SENTIMIENTO (OPTIMIZADO) ---
with tab3:
    st.subheader("Indicador de Pánico y Codicia")
    spy_h = yf.Ticker("SPY").history(period="1y")
    val = ta.rsi(spy_h['Close'], length=14).iloc[-1]
    
    if val < 30: etiq, col = "PÁNICO EXTREMO", "red"
    elif val < 45: etiq, col = "MIEDO", "orange"
    elif val < 60: etiq, col = "NEUTRAL", "gray"
    elif val < 75: etiq, col = "CODICIA", "lightgreen"
    else: etiq, col = "EUFORIA EXTREMA", "green"

    fig_sent = go.Figure(go.Indicator(
        mode = "gauge+number", value = val,
        title = {'text': f"Estado: {etiq}"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': col},
                 'steps': [{'range': [0, 30], 'color': "red"}, {'range': [30, 70], 'color': "gray"}, {'range': [70, 100], 'color': "green"}]}
    ))
    fig_sent.update_layout(height=300, template="plotly_dark")
    st.plotly_chart(fig_sent, use_container_width=True)
