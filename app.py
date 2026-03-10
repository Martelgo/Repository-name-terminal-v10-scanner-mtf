import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO
import requests
import time

# Configuración visual de la Terminal
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global Autónomo")

# --- 0. CONFIGURACIÓN TELEGRAM (SIDEBAR) ---
st.sidebar.header("🤖 Configuración Bot Telegram")
tel_token = st.sidebar.text_input("Bot Token:", type="password", help="Consíguelo con @BotFather")
tel_chatid = st.sidebar.text_input("Chat ID:", help="Consíguelo con @userinfobot")

def enviar_telegram(mensaje):
    if tel_token and tel_chatid:
        url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
        payload = {"chat_id": tel_chatid, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except:
            pass

# --- 1. OBTENCIÓN AUTOMÁTICA DE TICKERS ---
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
        
        bmv_tickers = [
            "WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
            "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX",
            "ALFAA.MX", "BIMBOA.MX", "GRUMAB.MX", "ORBIA.MX", "KIMBERA.MX"
        ]
        
        return {"S&P 500": sp500_tickers, "NASDAQ 100": nasdaq_tickers, "BMV (México)": bmv_tickers}
    except Exception as e:
        st.error(f"⚠️ Error al conectar con fuentes: {e}")
        return {}

# --- 2. MOTOR DE PROCESAMIENTO CON ESCUDO ANTI-BLOQUEO ---
def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Escaneando {nombre_mercado}: {t} ({i+1}/{total})")
            time.sleep(0.5) # Pausa estratégica anti-bloqueo
            
            tk = yf.Ticker(t)
            p = tk.fast_info['last_price']
            info = tk.info
            
            target = info.get('targetMeanPrice', p)
            margen = ((target - p) / p) * 100 if p else 0
            ebitda = info.get('ebitda', 0) or 0
            
            n1 = round(p * 0.96, 2)
            
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
                # Alerta Telegram si toca el Nivel 1
                if p <= n1:
                    msg = f"🚨 *ALERTA V10:* {t} en zona de compra.\nPrecio: ${p:.2f}\nMargen: {margen:.1f}%"
                    enviar_telegram(msg)
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue 
                
            resultados.append({
                "Mercado": nombre_mercado, "Ticker": t, "Estado": estado,
                "Precio": round(p, 2), "Margen %": round(margen, 1), "Nivel 1": n1
            })
        except Exception as e:
            if "RateLimitError" in str(e):
                monitor_text.text("⏳ Límite de Yahoo. Pausa de 30 seg...")
                time.sleep(30)
            continue
        progreso_bar.progress((i + 1) / total)
    
    return resultados

# --- 3. INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades Global")
    universo = obtener_universo_autonomo()
    
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            mercado_selec = st.selectbox("Mercado Específico:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear {mercado_selec}")
        with c2:
            btn_global = st.button("🌍 EJECUTAR ESCANEO GLOBAL")

        df_final = pd.DataFrame()
        if btn_solo or btn_global:
            progreso = st.progress(0); monitor = st.empty()
            if btn_solo:
                datos = procesar_lista_tickers(universo[mercado_selec], mercado_selec, progreso, monitor)
                df_final = pd.DataFrame(datos)
            else:
                todas = []
                for m_nom, m_tics in universo.items():
                    res = procesar_lista_tickers(m_tics, m_nom, progreso, monitor)
                    todas.extend(res)
                df_final = pd.DataFrame(todas)
            monitor.empty()

        if not df_final.empty:
            df_final = df_final.drop_duplicates(subset=['Ticker'])
            st.success(f"✅ {len(df_final)} oportunidades detectadas.")
            st.dataframe(df_final.sort_values(by="Margen %", ascending=False), use_container_width=True)

with tab2:
    st.subheader("Auditoría Individual Elite")
    tk_audit = st.text_input("Ingrese Ticker (ej: ORCL, TSLA, WALMEX.MX):", "").upper()
    
    if tk_audit:
        with st.spinner(f"Generando Informe V10 para {tk_audit}..."):
            acc = yf.Ticker(tk_audit)
            try:
                info = acc.info
                hist = acc.history(period="1y")
                precio_act = acc.fast_info['last_price']
                
                if not hist.empty:
                    # Lógica de Datos
                    target = info.get('targetMeanPrice', precio_act)
                    margen_seg = ((target - precio_act) / precio_act) * 100
                    ebitda_val = info.get('ebitda', 0)
                    rsi_val = ta.rsi(hist['Close'], length=14).iloc[-1]
                    sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                    
                    # Estados Semánticos
                    est_margen = "✅ DESCUENTO" if margen_seg > 15 else "❌ CARO"
                    est_rsi = "⚖️ NEUTRAL" if 30 <= rsi_val <= 70 else ("🔥 SOBREVENTA" if rsi_val < 30 else "🧊 SOBRECOMPRA")
                    est_sma = "🚀 ALCISTA" if precio_act > sma200 else "⚠️ BAJISTA"
                    est_ebitda = "✅ Sólido" if ebitda_val > 0 else "❌ Débil"
                    estrategia = "CONTINUACION (Acción en descuento)" if margen_seg > 10 else "ESPERAR (Precio elevado)"

                    # --- RECUADRO PROFESIONAL (V10 STYLE) ---
                    st.markdown(f"### 🏢 {info.get('longName', tk_audit)}")
                    st.markdown(f"**🔬 ESTRATEGIA: {estrategia}**")
                    
                    cuadro = f"""
                    ```text
                    =================================================================
                              MÉTRICA           VALOR          ESTADO
                    -----------------------------------------------------------------
                         Precio Actual       $ {precio_act:>8.2f}    Cotizando
                    Precio Justo de la Acción $ {target:>8.2f}    Referencia
                           Margen Seg.         {margen_seg:>8.1f}%    {est_margen}
                            RSI (14d)          {rsi_val:>8.1f}    {est_rsi}
                             SMA 200         $ {sma200:>8.2f}    {est_sma}
                             EBITDA            {ebitda_val:>14,.0}    {est_ebitda}
                    -----------------------------------------------------------------
                    📍 NIVEL DE COMPRA:  1: ${precio_act*0.96:.2f} | 2: ${precio_act*0.92:.2f} | 3: ${precio_act*0.88:.2f}
                    =================================================================
                    ```
                    """
                    st.markdown(cuadro)

                    # Gráfico
                    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Precio")])
                    hist['SMA200_p'] = hist['Close'].rolling(window=200).mean()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200_p'], name="SMA 200", line=dict(color='orange', width=2)))
                    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("Ticker no encontrado o sin datos.")
            except:
                st.error("Error de conexión. Intente en 1 minuto.")

with tab3:
    st.subheader("Sentimiento del Mercado")
    spy = yf.Ticker("SPY").history(period="1mo")
    if not spy.empty:
        rsi_spy = ta.rsi(spy['Close'], length=14).iloc[-1]
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = rsi_spy,
            title = {'text': "Sentimiento (RSI SPY)"},
            gauge = {
                'axis': {'range': [0, 100]},
                'steps': [
                    {'range': [0, 30], 'color': "red"},
                    {'range': [30, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "green"}]
            }
        ))
        fig_gauge.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)
