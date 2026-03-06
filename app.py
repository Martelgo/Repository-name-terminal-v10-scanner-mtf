import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Configuración de página
st.set_page_config(page_title="V10 Institutional Scanner", layout="wide")

st.title("🚀 V10 Institutional Strategy Scanner")
st.markdown("### Detección de tendencia institucional y pullbacks de alta precisión")

# --- FUNCIONES DE CÁLCULO ---
def get_v10_data(ticker):
    try:
        # Descarga eficiente: Solo lo necesario para las EMAs
        df_1d = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df_1d) < 200: return None
        
        # Filtro Estructural Daily (Check inmediato para ahorrar recursos)
        ema200_1d = ta.ema(df_1d['Close'], length=200).iloc[-1]
        ema50_1d = ta.ema(df_1d['Close'], length=50).iloc[-1]
        price_now = df_1d['Close'].iloc[-1]
        
        if not (price_now > ema200_1d and ema50_1d > ema200_1d):
            return None # Descartado
            
        # Si pasa el filtro Daily, descargamos el resto
        df_4h = yf.download(ticker, period="1mo", interval="1h", progress=False)
        df_15m = yf.download(ticker, period="5d", interval="15m", progress=False)
        
        score = 4 # Ya tiene 4 puntos por pasar el filtro Daily
        
        # Momentum 4H
        ema9_4h = ta.ema(df_4h['Close'], length=9).iloc[-1]
        ema50_4h = ta.ema(df_4h['Close'], length=50).iloc[-1]
        if ema9_4h > ema50_4h: score += 3
        
        # Pullback 15M
        ema9_15m = ta.ema(df_15m['Close'], length=9).iloc[-1]
        ema50_15m = ta.ema(df_15m['Close'], length=50).iloc[-1]
        price_15m = df_15m['Close'].iloc[-1]
        if min(ema9_15m, ema50_15m) < price_15m < max(ema9_15m, ema50_15m):
            score += 2
            
        # Volumen
        vol_actual = df_15m['Volume'].iloc[-1]
        vol_avg = df_15m['Volume'].rolling(20).mean().iloc[-1]
        vol_mult = round(vol_actual / vol_avg, 2)
        if vol_actual > (1.2 * vol_avg): score += 1
        
        return {
            "Ticker": ticker,
            "Precio": f"${price_now:,.2f}",
            "Score": score,
            "Vol x": vol_mult,
            "Estado": "COMPRA CONFIRMADA" if score >= 9 else ("SECTOR PREPARADO" if score == 8 else "VIGILAR")
        }
    except:
        return None

# --- INTERFAZ DE STREAMLIT ---
with st.sidebar:
    st.header("Configuración")
    min_score = st.slider("Score Mínimo", 7, 10, 7)
    mercado = st.multiselect("Mercados", ["S&P 500", "NASDAQ 100", "BMV"], default=["S&P 500"])
    ejecutar = st.button("Escanear Mercado")

if ejecutar:
    # Aquí iría la lógica para obtener los tickers según la selección
    # Por ahora usaremos una lista de prueba para mostrar la potencia del dashboard
    tickers_test = ["NVDA", "AAPL", "MSFT", "AMD", "TSLA", "META", "GOOGL", "AMZN", "WALMEX.MX", "GFNORTEO.MX"]
    
    results = []
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers_test):
        res = get_v10_data(t.replace('.', '-'))
        if res and res['Score'] >= min_score:
            results.append(res)
        progress_bar.progress((i + 1) / len(tickers_test))
        
    if results:
        df = pd.DataFrame(results)
        
        # Estilo de la tabla
        def color_score(val):
            color = 'green' if val >= 9 else ('orange' if val == 8 else 'white')
            return f'color: {color}'

        st.dataframe(df.style.applymap(color_score, subset=['Score']), use_container_width=True)
    else:
        st.warning("No se encontraron activos que cumplan con los criterios en este momento.")
