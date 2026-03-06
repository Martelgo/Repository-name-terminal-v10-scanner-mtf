import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="V10 Institutional Scanner", layout="wide")

st.title("🚀 V10 Institutional Strategy Scanner")
st.markdown("### Enfoque: Tendencia Institucional y Pullbacks")

# --- LÓGICA DE PROCESAMIENTO ---
@st.cache_data(ttl=3600)  # Caché de 1 hora para no saturar descargas
def get_v10_analysis(ticker):
    try:
        # 1. Filtro Estructural Daily
        df_1d = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df_1d) < 200: return None
        
        ema200_1d = ta.ema(df_1d['Close'], length=200).iloc[-1]
        ema50_1d = ta.ema(df_1d['Close'], length=50).iloc[-1]
        price_now = df_1d['Close'].iloc[-1]
        
        # Regla de oro institucional: Precio > EMA200 y EMA50 > EMA200
        pass_daily = price_now > ema200_1d and ema50_1d > ema200_1d
        if not pass_daily: return None # Descarte inmediato

        score = 4 
        
        # 2. Momentum 4H (Usamos 1h como base técnica)
        df_4h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        ema9_4h = ta.ema(df_4h['Close'], length=9).iloc[-1]
        ema50_4h = ta.ema(df_4h['Close'], length=50).iloc[-1]
        if ema9_4h > ema50_4h: score += 3
        
        # 3. Pullback 15M
        df_15m = yf.download(ticker, period="5d", interval="15m", progress=False)
        ema9_15m = ta.ema(df_15m['Close'], length=9).iloc[-1]
        ema50_15m = ta.ema(df_15m['Close'], length=50).iloc[-1]
        price_15m = df_15m['Close'].iloc[-1]
        
        if min(ema9_15m, ema50_15m) < price_15m < max(ema9_15m, ema50_15m):
            score += 2
            
        # 4. Volumen
        vol_actual = df_15m['Volume'].iloc[-1]
        vol_avg = df_15m['Volume'].rolling(20).mean().iloc[-1]
        vol_mult = round(vol_actual / vol_avg, 2)
        if vol_actual > (1.2 * vol_avg): score += 1
        
        return {
            "Ticker": ticker,
            "Precio": round(float(price_now), 2),
            "Score": score,
            "Vol x": vol_mult,
            "Estado": "COMPRA CONFIRMADA" if score >= 9 else ("SECTOR PREPARADO" if score == 8 else "VIGILAR")
        }
    except Exception:
        return None

# --- INTERFAZ LATERAL ---
with st.sidebar:
    st.header("Configuración")
    mercado = st.radio("Selecciona Mercado", ["EUA (NYSE/NASDAQ)", "México (BMV)"])
    tickers_input = st.text_area("Escribe los Tickers (separados por coma)", "NVDA, MSFT, AAPL, AMD")
    ejecutar = st.button("Analizar V10")

# --- PROCESAMIENTO ---
if ejecutar:
    # Limpiar y preparar lista de tickers
    raw_list = [t.strip().upper() for t in tickers_input.split(",")]
    final_tickers = []
    
    for t in raw_list:
        if mercado == "México (BMV)" and not t.endswith(".MX"):
            final_tickers.append(f"{t}.MX")
        else:
            final_tickers.append(t)

    results = []
    with st.spinner(f"Analizando {len(final_tickers)} activos..."):
        for t in final_tickers:
            res = get_v10_analysis(t)
            if res:
                results.append(res)
    
    if results:
        df = pd.DataFrame(results)
        
        # Formato visual
        def color_status(val):
            if val == "COMPRA CONFIRMADA": return 'background-color: #004d00; color: white'
            if val == "SECTOR PREPARADO": return 'background-color: #4d4d00; color: white'
            return ''

        st.subheader("Resultados del Scanner")
        st.dataframe(df.style.applymap(color_status, subset=['Estado']), use_container_width=True)
    else:
        st.info("Ninguno de los activos ingresados cumple con el filtro institucional (Precio > EMA 200).")
