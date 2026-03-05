import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

st.set_page_config(page_title="V10 Scanner", layout="wide")

st.title("🚀 V10 Scanner MTF")

st.markdown("Scanner institucional con **EMA 9 / 50 / 200 + volumen**")

# -------------------------
# UNIVERSOS
# -------------------------

@st.cache_data
def get_sp500():
    table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    return table[0]["Symbol"].tolist()

@st.cache_data
def get_nasdaq100():
    table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
    return table[4]["Ticker"].tolist()

def get_bmv():
    return [
        "WALMEX.MX","AMX.MX","GMEXICOB.MX","FEMSAUBD.MX",
        "GFNORTEO.MX","BIMBOA.MX","CEMEXCPO.MX"
    ]

def universo_total():
    return list(set(get_sp500() + get_nasdaq100() + get_bmv()))

# -------------------------
# SCANNER
# -------------------------

def scan_market():

    tickers = universo_total()

    resultados = []

    for t in tickers[:150]:

        try:

            info = yf.Ticker(t).info
            ebitda = info.get("ebitda",0)

            if ebitda <= 0:
                continue

            daily = yf.download(t, period="6mo", interval="1d", progress=False)

            if len(daily) < 200:
                continue

            daily["EMA9"] = ta.ema(daily["Close"], length=9)
            daily["EMA50"] = ta.ema(daily["Close"], length=50)
            daily["EMA200"] = ta.ema(daily["Close"], length=200)

            trend = (
                daily["Close"].iloc[-1] > daily["EMA200"].iloc[-1]
                and daily["EMA9"].iloc[-1] > daily["EMA50"].iloc[-1]
            )

            if not trend:
                continue

            m15 = yf.download(t, period="5d", interval="15m", progress=False)

            m15["EMA9"] = ta.ema(m15["Close"], length=9)
            m15["EMA50"] = ta.ema(m15["Close"], length=50)

            vol_avg = m15["Volume"].rolling(20).mean()

            entry = abs(
                m15["Close"].iloc[-1] - m15["EMA9"].iloc[-1]
            ) / m15["EMA9"].iloc[-1] < 0.01

            vol = m15["Volume"].iloc[-1] > vol_avg.iloc[-1] * 1.5

            if entry and vol:

                resultados.append({
                    "Ticker": t,
                    "Precio": round(m15["Close"].iloc[-1],2),
                    "Volumen x": round(m15["Volume"].iloc[-1] / vol_avg.iloc[-1],2)
                })

        except:
            continue

    return pd.DataFrame(resultados)

# -------------------------
# INTERFAZ
# -------------------------

st.subheader("⚡ Scanner institucional")

if st.button("Escanear mercado"):

    with st.spinner("Escaneando mercado completo..."):

        df = scan_market()

    if not df.empty:

        st.success(f"{len(df)} setups detectados")

        st.dataframe(df)

    else:

        st.warning("No se encontraron setups")
