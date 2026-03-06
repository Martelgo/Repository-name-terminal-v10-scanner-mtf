import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO

# Configuración visual de la App
st.set_page_config(page_title="V10 Elite Terminal", layout="wide")
st.title("🛰️ Terminal V10 Pro - Sistema Autónomo")

# --- FUNCIONES DE EXTRACCIÓN (WIKIPEDIA FIX) ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        # 1. S&P 500
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp, storage_options=headers)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        # 2. NASDAQ 100
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
        st.error(f"⚠️ Error al conectar con fuentes: {e}")
        return {}

# --- MOTOR DE ESCANEO V10 ---
@st.cache_data(ttl=3600)
def ejecutar_escaneo_v10(lista_tickers, nombre_mercado):
    resultados = []
    progreso = st.progress(0)
    monitor = st.empty()
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            monitor.text(f"🔍 Analizando {t} ({i+1}/{total}) en {nombre_mercado}")
            tk = yf.Ticker(t)
            
            # Datos rápidos de precio
            p = tk.fast_info['last_price']
            info = tk.info
            
            # Lógica de Valoración V10
            target = info.get('targetMeanPrice')
            eps = info.get('forwardEps')
            pe = info.get('forwardPE', 15)
            ebitda = info.get('ebitda', 0) or 0
            
            # Fallback: si no hay target oficial, calculamos uno basado en PER * EPS
            p_justo = target if target else (pe * eps if eps else p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            
            # FILTRO ESTRICTO V10
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue # Descartar si no cumple
                
            resultados.append({
                "Mercado": nombre_mercado,
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

# --- NAVEGACIÓN ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

# --- TAB 1: RADAR (CON EXCEL) ---
with tab1:
    st.subheader("Radar de Oportunidades")
    universo = obtener_universo_autonomo()
    
    if universo:
        mercado_selec = st.selectbox("Selecciona Mercado:", list(universo.keys()))
        
        if st.button(f"🚀 Iniciar Escaneo de {mercado_selec}"):
            lista_activos = universo[mercado_selec]
            df_res = ejecutar_escaneo_v10(lista_activos, mercado_selec)
            
            if not df_res.empty:
                st.success("✅ Escaneo Completo")
                
                # Métricas de resumen
                m1, m2 = st.columns(2)
                m1.metric("Analizados", len(lista_activos))
                m2.metric("Oportunidades", len(df_res))
                
                # Preparar Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_res.to_excel(writer, index=False, sheet_name='V10_Report')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Descargar Reporte en Excel",
                    data=excel_data,
                    file_name=f'V10_{mercado_selec}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # Mostrar Tabla Enumerada
                df_res.index = range(1, len(df_res) + 1)
                st.dataframe(df_res.sort_values(by="Margen %", ascending=False), use_container_width=True)
            else:
                st.warning("No se hallaron oportunidades bajo los criterios actuales.")
    else:
        st.error("No se pudo cargar el universo de acciones.")

# --- TAB 2: AUDITORIA ---
with tab2:
    st.subheader("Análisis Individual")
    tk_in = st.text_input("Ticker:", "MSFT").upper()
    if tk_in:
        acc = yf.Ticker(tk_in)
        h = acc.history(period="1y")
        if not h.empty:
            st.markdown(f"### {tk_in}")
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SENTIMIENTO ---
with tab3:
    st.subheader("Sentimiento Global")
    spy = yf.Ticker("SPY").history(period="1mo")
    rsi_val = ta.rsi(spy['Close'], length=14).iloc[-1]
    st.metric("RSI S&P 500 (SPY)", f"{rsi_val:.2f}")
    st.info("💡 RSI < 30 = Pánico | RSI > 70 = Euforia")
