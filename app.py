import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import requests
import time

# Configuración de página
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
        try: requests.post(url, json=payload)
        except: pass

# --- OBTENCIÓN DE UNIVERSO DE TICKERS ---
@st.cache_data(ttl=86400)
def obtener_universo():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # S&P 500
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp_df = pd.read_html(url_sp, storage_options=headers)[0]
        sp_tics = sp_df['Symbol'].str.replace('.', '-').tolist()
        # NASDAQ 100
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nas_df = pd.read_html(url_nas, storage_options=headers)[4]
        nas_tics = nas_df['Ticker'].tolist()
        # BMV Selección Pro
        bmv_tics = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "ASURB.MX", "GAPB.MX", "CEMEXCPO.MX"]
        return {"S&P 500": sp_tics, "NASDAQ 100": nas_tics, "BMV (México)": bmv_tics}
    except: return {}

# --- MOTOR DE ESCANEO ---
def motor_v10(lista, nombre_m, p_bar, m_text):
    res = []
    for i, t in enumerate(lista):
        try:
            m_text.text(f"🔍 Escaneando {nombre_m}: {t} ({i+1}/{len(lista)})")
            time.sleep(0.5) # Escudo anti-bloqueo
            tk = yf.Ticker(t)
            p = tk.fast_info['last_price']
            info = tk.info
            tgt = info.get('targetMeanPrice', p)
            margen = ((tgt - p) / p) * 100 if p else 0
            ebitda = info.get('ebitda', 0) or 0
            
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
                if p <= (p * 0.96): enviar_telegram(f"🚨 *V10 COMPRA:* {t}\nPrecio: ${p:.2f}")
                res.append({"Ticker": t, "Estado": estado, "Precio": round(p, 2), "Margen %": round(margen, 1)})
        except: continue
        p_bar.progress((i + 1) / len(lista))
    return res

# --- INTERFAZ DE TABS ---
t1, t2, t3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with t1:
    universo = obtener_universo()
    c1, c2 = st.columns(2)
    with c1:
        m_sel = st.selectbox("Mercado:", list(universo.keys()))
        b_solo = st.button(f"🚀 Escanear {m_sel}")
    with c2:
        b_global = st.button("🌍 ESCANEO GLOBAL")

    df_radar = pd.DataFrame()
    if b_solo or b_global:
        pb = st.progress(0); mt = st.empty()
        if b_solo: df_radar = pd.DataFrame(motor_v10(universo[m_sel], m_sel, pb, mt))
        else:
            total = []
            for k, v in universo.items(): total.extend(motor_v10(v, k, pb, mt))
            df_radar = pd.DataFrame(total)
        mt.empty()
    
    if not df_radar.empty:
        st.dataframe(df_radar.sort_values("Margen %", ascending=False), use_container_width=True)

with t2:
    st.subheader("Análisis 360 de Activo")
    cm, ct = st.columns([1, 2])
    with cm:
        tipo = st.radio("Mercado:", ["EUA (Gringo)", "México (BMV)"], horizontal=True)
    with ct:
        tk_in = st.text_input("Ticker:", "ORCL").upper()
    
    tk_final = f"{tk_in}.MX" if tipo == "México (BMV)" and not tk_in.endswith(".MX") else tk_in

    if tk_final:
        with st.spinner("Generando Informe..."):
            try:
                acc = yf.Ticker(tk_final)
                h = acc.history(period="1y")
                inf = acc.info
                p_act = acc.fast_info['last_price']
                
                if not h.empty:
                    tgt = inf.get('targetMeanPrice', p_act)
                    mgn = ((tgt - p_act) / p_act) * 100
                    rsi = ta.rsi(h['Close']).iloc[-1]
                    sma = h['Close'].rolling(200).mean().iloc[-1]
                    ebit = inf.get('ebitda', 0)
                    
                    est_m = "✅ DESCUENTO" if mgn > 15 else "❌ CARO"
                    est_r = "⚖️ NEUTRAL" if 30 < rsi < 70 else "🔥 ZONA CLAVE"
                    est_s = "🚀 ALCISTA" if p_act > sma else "⚠️ BAJISTA"
                    strat = "CONTINUACION (Acción en descuento)" if mgn > 10 else "ESPERAR (Precio elevado)"

                    st.markdown(f"### 🏢 {inf.get('longName', tk_final)}")
                    st.markdown(f"**🔬 ESTRATEGIA: {strat}**")
                    
                    st.markdown(f"""
                    ```text
                    =================================================================
                              MÉTRICA           VALOR          ESTADO
                    -----------------------------------------------------------------
                         Precio Actual       $ {p_act:>8.2f}    Cotizando
                    Precio Justo de la Acción $ {tgt:>8.2f}    Referencia
                           Margen Seg.         {mgn:>8.1f}%    {est_m}
                            RSI (14d)          {rsi:>8.1f}    {est_r}
                             SMA 200         $ {sma:>8.2f}    {est_s}
                             EBITDA            {ebit:>14,.0}    {'✅ Sólido' if ebit>0 else '❌ Débil'}
                    -----------------------------------------------------------------
                    📍 NIVEL DE COMPRA:  1: ${p_act*0.96:.2f} | 2: ${p_act*0.92:.2f} | 3: ${p_act*0.88:.2f}
                    =================================================================
                    ```
                    """)
                    fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
                    fig.add_trace(go.Scatter(x=h.index, y=h['Close'].rolling(200).mean(), name="SMA 200", line=dict(color='orange')))
                    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450)
                    st.plotly_chart(fig, use_container_width=True)
            except: st.error("Error de conexión. Intente en 1 minuto.")

with t3:
    spy_h = yf.Ticker("SPY").history(period="1mo")
    if not spy_h.empty:
        r_spy = ta.rsi(spy_h['Close']).iloc[-1]
        st.metric("Sentimiento del Mercado (RSI SPY)", f"{r_spy:.1f}")
        st.progress(r_spy/100)
