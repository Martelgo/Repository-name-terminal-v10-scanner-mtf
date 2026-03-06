import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# Configuración visual de la App
st.set_page_config(page_title="V10 Elite Terminal", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Autónomo")

# --- FUNCIONES DE EXTRACCIÓN AUTOMÁTICA (CORREGIDAS) ---
@st.cache_data(ttl=86400) # Se guarda 24h para no saturar Wikipedia
def obtener_universo_autonomo():
    try:
        # User-Agent para evitar Error 403 Forbidden
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # 1. S&P 500 de Wikipedia
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp, storage_options=headers)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        # 2. NASDAQ 100 de Wikipedia
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(url_nas, storage_options=headers)[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        
        # 3. BMV (Principales)
        bmv_tickers = ["WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
                       "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX"]
        
        return {
            "S&P 500": sp500_tickers,
            "NASDAQ 100": nasdaq_tickers,
            "BMV (México)": bmv_tickers
        }
    except Exception as e:
        st.error(f"⚠️ Error al conectar con las fuentes de índices: {e}")
        return {}

@st.cache_data(ttl=3600) # Actualiza el análisis cada hora
def ejecutar_escaneo_v10(lista_tickers):
    resultados = []
    progreso = st.progress(0)
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            ticker = yf.Ticker(t)
            # fast_info es clave para velocidad en listas largas
            p = ticker.fast_info['last_price']
            info = ticker.info
            
            # Lógica Fundamental V10
            tj = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
            ebitda = info.get('ebitda', 0) or 0
            m = ((tj - p) / p) * 100 if p else 0
            
            # FILTRO: Solo Compra Clara o Vigilar (Lo demás se descarta)
            if m > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
            elif m > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue 
                
            resultados.append({
                "Ticker": t,
                "Estado": estado,
                "Precio": round(p, 2),
                "Margen %": round(m, 1),
                "Sector": info.get('sector', 'N/A')
            })
        except:
            continue
        progreso.progress((i + 1) / total)
    
    return pd.DataFrame(resultados)

# --- NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR ---
with tab1:
    st.subheader("Radar de Oportunidades Filtradas")
    mercado_selec = st.selectbox("Selecciona el Mercado a Analizar:", ["S&P 500", "NASDAQ 100", "BMV (México)"])
    
    if st.button(f"🚀 Iniciar Escaneo de {mercado_selec}"):
        universo = obtener_universo_autonomo()
        lista_activos = universo.get(mercado_selec, [])
        
        if lista_activos:
            st.info(f"Analizando {len(lista_activos)} activos... Esto puede tardar unos minutos.")
            df_resultados = ejecutar_escaneo_v10(lista_activos)
            
            if not df_resultados.empty:
                st.success(f"¡Escaneo listo! Se encontraron {len(df_resultados)} activos prometedores.")
                st.dataframe(df_resultados.sort_values(by="Margen %", ascending=False), use_container_width=True)
            else:
                st.warning("No se encontraron activos que cumplan con los criterios V10 en este momento.")
    else:
        st.info("Haz clic en el botón para buscar oportunidades en el mercado seleccionado.")

# --- TAB 2: AUDITORIA (CONSOLA ORIGINAL) ---
with tab2:
    st.subheader("Análisis 360 de Activo")
    c_i1, c_i2 = st.columns([1, 2])
    with c_i1: mkt = st.radio("Mercado:", ["EUA", "México (.MX)"])
    with c_i2: tk_in = st.text_input("Ticker:", "MSFT").upper()

    ticker_final = tk_in if mkt == "EUA" else (f"{tk_in}.MX" if ".MX" not in tk_in else tk_in)

    if ticker_final:
        with st.spinner('Auditando...'):
            acc = yf.Ticker(ticker_final)
            h = acc.history(period="1y")
            info = acc.info
            if not h.empty:
                h['RSI'] = ta.rsi(h['Close'], length=14)
                h['SMA200'] = ta.sma(h['Close'], length=200)
                p_act = h['Close'].iloc[-1]
                rsi_v = h['RSI'].iloc[-1] if not pd.isna(h['RSI'].iloc[-1]) else 50
                sma_v = h['SMA200'].iloc[-1] if not pd.isna(h['SMA200'].iloc[-1]) else p_act
                
                p_justo = info.get('targetMeanPrice') or (info.get('forwardPE', 15) * info.get('forwardEps', 1))
                margen = ((p_justo - p_act) / p_act) * 100
                ebitda = info.get('ebitda', 0) or 0
                
                reporte_v2 = f"""
=================================================================
 MÉTTRICA            VALOR       ESTADO
-----------------------------------------------------------------
 Precio Actual       ${p_act:>8.2f}    Cotizando
 Precio Justo        ${p_justo:>8.2f}    Referencia
 Margen Seg.         {margen:>7.1f}%     {"✅" if margen>15 else "❌"}
 RSI (14d)           {rsi_v:>7.1f}  {"📉" if rsi_v<35 else "⚖️"}
 SMA 200             ${sma_v:>8.2f}    {"🚀" if p_act>sma_v else "⚠️"}
 EBITDA              {ebitda:>14,}      {"✅" if ebitda>0 else "⚠️"}
=================================================================
"""
                st.markdown(f"### 🏢 {info.get('longName', ticker_final)}")
                st.code(reporte_v2, language="text")
                
                fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
                fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SENTIMIENTO ---
with tab3:
    st.subheader("Indicador de Pánico y Codicia")
    spy_h = yf.Ticker("SPY").history(period="1y")
    val = ta.rsi(spy_h['Close'], length=14).iloc[-1]
    
    fig_sent = go.Figure(go.Indicator(
        mode = "gauge+number", value = val,
        title = {'text': "RSI SPY (Market Sentiment)"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "lightgreen" if val > 50 else "red"}}
    ))
    fig_sent.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig_sent, use_container_width=True)
    st.info("💡 Pánico < 30 | Euforia > 70")
