import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from io import BytesIO

st.set_page_config(page_title="V10 Institutional Scanner", layout="wide")

st.title("🚀 V10 Institutional Strategy Scanner")

# --- MOTOR DE ANÁLISIS MEJORADO ---
def analizar_activo_v10(ticker):
    try:
        df_1d = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df_1d.empty or len(df_1d) < 200:
            return {"Ticker": ticker, "Estado": "Datos Insuficientes", "Score": 0}

        # Valores actuales
        price_now = df_1d['Close'].iloc[-1]
        ema200_1d = ta.ema(df_1d['Close'], length=200).iloc[-1]
        ema50_1d = ta.ema(df_1d['Close'], length=50).iloc[-1]

        # FILTRO 1: Tendencia Estructural
        condicion_alcista = price_now > ema200_1d and ema50_1d > ema200_1d
        
        if not condicion_alcista:
            return {
                "Ticker": ticker, 
                "Precio": round(float(price_now), 2),
                "Score": 0, 
                "Estado": "FUERA DE TENDENCIA (Precio < EMA200)",
                "Vol x": 0
            }

        # Si pasa, calculamos el Score completo
        score = 4
        
        # Momentum 4H
        df_4h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        ema9_4h = ta.ema(df_4h['Close'], length=9).iloc[-1]
        ema50_4h = ta.ema(df_4h['Close'], length=50).iloc[-1]
        if ema9_4h > ema50_4h: score += 3
        
        # Pullback 15M
        df_15m = yf.download(ticker, period="5d", interval="15m", progress=False)
        ema9_15m = ta.ema(df_15m['Close'], length=9).iloc[-1]
        ema50_15m = ta.ema(df_15m['Close'], length=50).iloc[-1]
        p_15m = df_15m['Close'].iloc[-1]
        if min(ema9_15m, ema50_15m) < p_15m < max(ema9_15m, ema50_15m): score += 2
            
        # Volumen
        v_act = df_15m['Volume'].iloc[-1]
        v_avg = df_15m['Volume'].rolling(20).mean().iloc[-1]
        v_mult = round(v_act / v_avg, 2)
        if v_act > (1.2 * v_avg): score += 1

        status = "COMPRA CONFIRMADA" if score >= 9 else ("SECTOR PREPARADO" if score == 8 else "VIGILAR")
        
        return {
            "Ticker": ticker, "Precio": round(float(price_now), 2),
            "Score": score, "Vol x": v_mult, "Estado": status
        }
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuración")
    mercado = st.radio("Mercado", ["EUA", "México"])
    txt_input = st.text_area("Tickers (ej: NVDA, WALMEX)", "WALMEX, AMXN, GFNORTEO")
    btn = st.button("Analizar V10")

if btn:
    tickers = [t.strip().upper() for t in txt_input.split(",")]
    if mercado == "México":
        tickers = [f"{t}.MX" if not t.endswith(".MX") else t for t in tickers]
    
    results = []
    for t in tickers:
        res = analizar_activo_v10(t)
        if res: results.append(res)
    
    if results:
        df = pd.DataFrame(results)
        st.subheader("Análisis de Portafolio V10")
        
        # Mostrar tabla
        st.dataframe(df, use_container_width=True)
        
        # Botón para Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Scanner_V10')
        
        st.download_button(
            label="📥 Descargar Reporte Excel",
            data=output.getvalue(),
            file_name="analisis_v10.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
