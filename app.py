import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Configuración visual
st.set_page_config(page_title="V10 Elite Terminal", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner de Alta Potencia")

# --- EXTRACCIÓN DE TICKERS (WIKIPEDIA FIX) ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', storage_options=headers)[0]
        lista_sp = sp500['Symbol'].str.replace('.', '-').tolist()
        
        # NASDAQ 100
        nasdaq = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100', storage_options=headers)[4]
        lista_nas = nasdaq['Ticker'].tolist()
        
        # BMV (Principales)
        lista_bmv = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", "GAPB.MX", "CEMEXCPO.MX"]
        
        return {"S&P 500": lista_sp, "NASDAQ 100": lista_nas, "BMV (México)": lista_bmv}
    except Exception as e:
        st.error(f"Error en fuentes: {e}")
        return {}

# --- MOTOR DE ESCANEO V10 ---
@st.cache_data(ttl=3600)
def ejecutar_escaneo_v10(lista_tickers):
    resultados = []
    progreso = st.progress(0)
    monitor = st.empty()
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            monitor.text(f"🔍 Analizando {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            
            # Datos Rápidos
            p = tk.fast_info['last_price']
            info = tk.info
            
            # Cálculo de Valor Intrínseco (Si no hay Target, usamos PER * EPS)
            target = info.get('targetMeanPrice')
            eps = info.get('forwardEps')
            pe = info.get('forwardPE', 15)
            ebitda = info.get('ebitda', 0) or 0
            
            p_justo = target if target else (pe * eps if eps else p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            
            # --- FILTRO V10 (SOLO COMPRA O VIGILAR) ---
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue # DESCARTAR
                
            resultados.append({
                "Ticker": t,
                "Estado": estado,
                "Precio": round(p, 2),
                "Margen %": round(margen, 1),
                "Sector": info.get('sector', 'N/A')
            })
        except:
            continue
        progreso.progress((i + 1) / total)
    
    monitor.empty()
    return pd.DataFrame(resultados)

# --- INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    mercado = st.selectbox("Selecciona Mercado:", list(universo.keys()))
    
    if st.button(f"🚀 Iniciar Escaneo de {mercado}"):
        df = ejecutar_escaneo_v10(universo[mercado])
        if not df.empty:
            st.success(f"Se encontraron {len(df)} oportunidades.")
            st.dataframe(df.sort_values(by="Margen %", ascending=False), use_container_width=True)
        else:
            st.warning("Sin oportunidades claras bajo los criterios V10.")

with tab2:
    st.subheader("Auditoría de Activo")
    tk_in = st.text_input("Ingresa Ticker (ej: MSFT o WALMEX.MX):", "MSFT").upper()
    if tk_in:
        acc = yf.Ticker(tk_in)
        info = acc.info
        h = acc.history(period="1y")
        if not h.empty:
            p_act = h['Close'].iloc[-1]
            st.metric(label=info.get('longName', tk_in), value=f"${p_act:.2f}")
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Sentimiento del Mercado")
    spy = yf.Ticker("SPY").history(period="1mo")
    rsi_spy = ta.rsi(spy['Close'], length=14).iloc[-1]
    st.metric("RSI S&P 500 (SPY)", f"{rsi_spy:.2f}")
    st.info("RSI < 30: Pánico (Compra) | RSI > 70: Euforia (Venta)")
