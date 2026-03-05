import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="V10 Scanner", layout="wide")

st.title("🚀 V10 Scanner MTF")
st.write("Scanner institucional con EMA 9 / 50 / 200 + volumen")

# -------------------------------------------------
# UNIVERSOS DE MERCADO
# -------------------------------------------------

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
        "WALMEX.MX",
        "AMX.MX",
        "GMEXICOB.MX",
        "FEMSAUBD.MX",
        "GFNORTEO.MX",
        "BIMBOA.MX",
        "CEMEXCPO.MX"
    ]


def universo_total():

    return list(set(get_sp500() + get_nasdaq100() + get_bmv()))


# -------------------------------------------------
# SCANNER
# -------------------------------------------------

def scan_market():

    tickers = universo_total()

    resultados = []

    for ticker in tickers:

        try:

            info = yf.Ticker(ticker).info
            ebitda = info.get("ebitda",0)

            # filtro fundamental
            if ebitda <= 0:
                continue

            # -------------------------
            # DAILY
            # -------------------------

            daily = yf.download(
                ticker,
                period="6mo",
                interval="1d",
                progress=False
            )

            if len(daily) < 200:
                continue

            daily["EMA9"] = ta.ema(daily["Close"], length=9)
            daily["EMA50"] = ta.ema(daily["Close"], length=50)
            daily["EMA200"] = ta.ema(daily["Close"], length=200)

            tendencia = (
                daily["Close"].iloc[-1] > daily["EMA200"].iloc[-1]
                and daily["EMA9"].iloc[-1] > daily["EMA50"].iloc[-1]
            )

            if not tendencia:
                continue

            # -------------------------
            # 15m
            # -------------------------

            m15 = yf.download(
                ticker,
                period="5d",
                interval="15m",
                progress=False
            )

            m15["EMA9"] = ta.ema(m15["Close"], length=9)
            m15["EMA50"] = ta.ema(m15["Close"], length=50)

            vol_prom = m15["Volume"].rolling(20).mean()

            entrada = abs(
                m15["Close"].iloc[-1] - m15["EMA9"].iloc[-1]
            ) / m15["EMA9"].iloc[-1] < 0.01

            volumen = (
                m15["Volume"].iloc[-1] > vol_prom.iloc[-1] * 1.5
            )

            if entrada and volumen:

                resultados.append({
                    "Ticker": ticker,
                    "Precio": round(m15["Close"].iloc[-1],2),
                    "Volumen x": round(
                        m15["Volume"].iloc[-1] /
                        vol_prom.iloc[-1],2)
                })

        except:

            continue

    return pd.DataFrame(resultados)


# -------------------------------------------------
# INTERFAZ
# -------------------------------------------------

st.subheader("⚡ Scanner institucional")

if st.button("Escanear mercado"):

    with st.spinner("Escaneando mercado..."):

        df = scan_market()

    if not df.empty:

        st.success(f"{len(df)} setups detectados")

        st.dataframe(
            df.sort_values("Volumen x", ascending=False),
            use_container_width=True
        )

    else:

        st.warning("No se encontraron setups")
