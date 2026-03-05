import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="V10 Scanner PRO", layout="wide")

st.title("🚀 V10 Scanner PRO")
st.write("Scanner institucional EMA 9 / 50 / 200 + volumen + multi-temporalidad")

# -------------------------------
# UNIVERSO
# -------------------------------

def get_sp500():
    return [
        "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","JPM","XOM",
        "V","UNH","MA","HD","PG","COST","ABBV","MRK","PEP","KO",
        "LLY","BAC","TMO","WMT","CRM","ACN","CSCO","ABT","ADBE","CMCSA",
        "NFLX","MCD","LIN","ORCL","DHR","AMD","INTC","TXN","QCOM","AMAT"
    ]

def get_nasdaq100():
    return [
        "NVDA","AAPL","MSFT","AMZN","META","TSLA","GOOGL","AVGO","COST","PEP",
        "CSCO","AMD","INTC","ADBE","QCOM","TXN","AMAT","MU","ADI","KLAC"
    ]

def get_bmv():
    return [
        "WALMEX.MX","AMX.MX","GMEXICOB.MX","FEMSAUBD.MX",
        "GFNORTEO.MX","BIMBOA.MX","CEMEXCPO.MX"
    ]

def universo_total():
    return list(set(get_sp500() + get_nasdaq100() + get_bmv()))

# -------------------------------
# SCANNER
# -------------------------------

def scan_market():

    tickers = universo_total()
    resultados = []

    for ticker in tickers:

        try:

            score = 0

            info = yf.Ticker(ticker).info
            ebitda = info.get("ebitda",0)

            if ebitda <= 0:
                continue

            # ---------------------
            # DAILY (tendencia)
            # ---------------------

            d = yf.download(ticker, period="6mo", interval="1d", progress=False)

            if len(d) < 200:
                continue

            d["EMA9"] = ta.ema(d["Close"], length=9)
            d["EMA50"] = ta.ema(d["Close"], length=50)
            d["EMA200"] = ta.ema(d["Close"], length=200)

            trend = (
                d["Close"].iloc[-1] > d["EMA200"].iloc[-1]
                and d["EMA50"].iloc[-1] > d["EMA200"].iloc[-1]
            )

            if trend:
                score += 3
            else:
                continue

            # ---------------------
            # 4H (estructura)
            # ---------------------

            h4 = yf.download(ticker, period="1mo", interval="1h", progress=False)

            h4["EMA9"] = ta.ema(h4["Close"], length=9)
            h4["EMA50"] = ta.ema(h4["Close"], length=50)

            estructura = h4["EMA9"].iloc[-1] > h4["EMA50"].iloc[-1]

            if estructura:
                score += 3

            # ---------------------
            # 15m (entrada)
            # ---------------------

            m15 = yf.download(ticker, period="5d", interval="15m", progress=False)

            m15["EMA9"] = ta.ema(m15["Close"], length=9)
            m15["EMA50"] = ta.ema(m15["Close"], length=50)

            precio = m15["Close"].iloc[-1]
            ema9 = m15["EMA9"].iloc[-1]
            ema50 = m15["EMA50"].iloc[-1]

            pullback = ema50 < precio < ema9 or ema9 < precio < ema50

            if pullback:
                score += 2

            # ---------------------
            # VOLUMEN
            # ---------------------

            vol_avg = m15["Volume"].rolling(20).mean()
            vol_actual = m15["Volume"].iloc[-1]

            volumen = vol_actual > vol_avg.iloc[-1] * 1.5

            if volumen:
                score += 2

            # ---------------------
            # CLASIFICACIÓN
            # ---------------------

            estado = ""

            if score >= 9:
                estado = "🟢 Compra confirmada"
            elif score == 8:
                estado = "🟡 Sector preparado"
            elif score >= 7:
                estado = "🔎 Vigilar"

            if score >= 7:

                resultados.append({
                    "Ticker": ticker,
                    "Precio": round(precio,2),
                    "Score": score,
                    "Vol x": round(vol_actual/vol_avg.iloc[-1],2),
                    "Estado": estado
                })

        except:
            continue

    return pd.DataFrame(resultados)

# -------------------------------
# INTERFAZ
# -------------------------------

st.subheader("⚡ Scanner institucional")

if st.button("Escanear mercado"):

    with st.spinner("Escaneando mercado..."):

        df = scan_market()

    if not df.empty:

        st.success(f"{len(df)} oportunidades detectadas")

        st.dataframe(
            df.sort_values("Score", ascending=False),
            use_container_width=True
        )

    else:

        st.warning("No se encontraron setups en este momento")
