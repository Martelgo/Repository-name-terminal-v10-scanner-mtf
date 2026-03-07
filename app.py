import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(page_title="V10.1 Elite Terminal", layout="wide")
st.title("🛰️ Terminal V10.1 Elite")

# Universo de vigilancia
universo = {
    "Tecnología EUA": ["MSFT","AAPL","NVDA","GOOGL"],
    "México": ["WALMEX.MX","AMX.MX","GFNORTEO.MX","FEMSAUBD.MX"],
    "Chips": ["AMD","TSM","ASML","AVGO"],
    "Consumo": ["AMZN","TSLA","MELI","NKE"]
}

# --- FUNCION SCORE CUANTITATIVO ---

def calcular_score(margen, rsi, tendencia, ebitda):

    score = 0
    
    # Margen fundamental
    if margen > 20:
        score += 30
    elif margen > 10:
        score += 20
    elif margen > 5:
        score += 10

    # RSI óptimo institucional
    if 40 <= rsi <= 60:
        score += 25
    elif 35 <= rsi <= 65:
        score += 15

    # Tendencia
    if tendencia == "ALCISTA":
        score += 25

    # Calidad negocio
    if ebitda > 0:
        score += 20

    return score


@st.cache_data(ttl=600)
def cargar_radar():

    datos = []

    for sector, tickers in universo.items():

        for t in tickers:

            try:

                tk = yf.Ticker(t)
                h = tk.history(period="1y")
                info = tk.info

                if h.empty:
                    continue

                precio = h['Close'].iloc[-1]

                h['RSI'] = ta.rsi(h['Close'], length=14)
                h['SMA50'] = ta.sma(h['Close'], length=50)
                h['SMA200'] = ta.sma(h['Close'], length=200)

                rsi = h['RSI'].iloc[-1]
                sma50 = h['SMA50'].iloc[-1]
                sma200 = h['SMA200'].iloc[-1]

                tendencia = "ALCISTA" if sma50 > sma200 else "BAJISTA"

                # Precio justo mejorado
                target = info.get('targetMeanPrice')
                eps = info.get('forwardEps')
                pe = info.get('forwardPE',15)

                precio_justo = target if target else (pe*eps if eps else precio)

                margen = ((precio_justo-precio)/precio)*100

                ebitda = info.get('ebitda',0) or 0

                score = calcular_score(margen,rsi,tendencia,ebitda)

                # Clasificación
                if score >= 70:
                    estado = "🔥 COMPRA FUERTE"
                elif score >= 50:
                    estado = "🟢 OPORTUNIDAD"
                elif score >= 35:
                    estado = "🟡 VIGILAR"
                else:
                    estado = "🔴 EVITAR"

                datos.append({
                    "Ticker":t,
                    "Sector":sector,
                    "Precio":round(precio,2),
                    "Margen %":round(margen,1),
                    "RSI":round(rsi,1),
                    "Score V10":score,
                    "Estado":estado
                })

            except:
                continue

    return pd.DataFrame(datos)


# --- TABS ---

tab1,tab2,tab3 = st.tabs(["🎯 RADAR","🔍 AUDITORIA","🌡️ SENTIMIENTO"])

# --- RADAR ---
with tab1:

    st.subheader("Radar Inteligente V10")

    df = cargar_radar()

    if not df.empty:

        df = df.sort_values(by="Score V10",ascending=False)

        st.dataframe(df,use_container_width=True)

        st.caption("🔥 Score >70 = oportunidad institucional")

# --- AUDITORIA ---
with tab2:

    st.subheader("Auditoría de Activo")

    ticker = st.text_input("Ticker","MSFT").upper()

    if ticker:

        tk = yf.Ticker(ticker)
        h = tk.history(period="1y")

        if not h.empty:

            h['SMA200'] = ta.sma(h['Close'],length=200)

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=h.index,
                open=h['Open'],
                high=h['High'],
                low=h['Low'],
                close=h['Close']
            ))

            fig.add_trace(go.Scatter(
                x=h.index,
                y=h['SMA200'],
                name="SMA200"
            ))

            fig.update_layout(
                template="plotly_dark",
                height=500,
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(fig,use_container_width=True)


# --- SENTIMIENTO ---
with tab3:

    spy = yf.Ticker("SPY")
    h = spy.history(period="6mo")

    rsi = ta.rsi(h['Close'],length=14).iloc[-1]

    st.metric("RSI S&P500",round(rsi,2))

    if rsi < 30:
        st.error("PÁNICO DE MERCADO")
    elif rsi > 70:
        st.success("EUFORIA")
    else:
        st.info("NEUTRAL")
