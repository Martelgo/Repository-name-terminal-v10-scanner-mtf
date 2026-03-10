
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from io import BytesIO
import requests  # Nueva librería para Telegram

# Configuración visual de la Terminal
st.set_page_config(page_title="V10 Elite Terminal Pro", layout="wide")
st.title("🛰️ Terminal V10 Pro - Escáner Global Autónomo")

# --- CONFIGURACIÓN TELEGRAM (SIDEBAR) ---
st.sidebar.header("🤖 Configuración Bot Telegram")
tel_token = st.sidebar.text_input("Bot Token:", type="password", help="Consíguelo con @BotFather")
tel_chatid = st.sidebar.text_input("Chat ID:", help="Consíguelo con @userinfobot")

def enviar_telegram(mensaje):
    if tel_token and tel_chatid:
        url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
        payload = {"chat_id": tel_chatid, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            st.error(f"Error enviando Telegram: {e}")

# --- 1. OBTENCIÓN AUTOMÁTICA DE TICKERS ---
@st.cache_data(ttl=86400)
def obtener_universo_autonomo():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        # S&P 500
        url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(url_sp, storage_options=headers)[0]
        sp500_tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        
        # NASDAQ 100
        url_nas = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(url_nas, storage_options=headers)[4]
        nasdaq_tickers = nasdaq_table['Ticker'].tolist()
        
        # BMV (Lista ampliada del IPC México)
        bmv_tickers = [
            "WALMEX.MX", "AMX.MX", "GFNORTEO.MX", "FEMSAUBD.MX", "GMEXICOB.MX", 
            "TLEVISAA.MX", "ASURB.MX", "BBAJIOO.MX", "GAPB.MX", "CEMEXCPO.MX",
            "ALFAA.MX", "ALPEKA.MX", "BIMBOA.MX", "GRUMAB.MX", "ORBIA.MX", 
            "PINFRA.MX", "KIMBERA.MX", "AC.MX", "LABB.MX", "OMAB.MX"
        ]
        
        return {
            "S&P 500": sp500_tickers,
            "NASDAQ 100": nasdaq_tickers,
            "BMV (México)": bmv_tickers
        }
    except Exception as e:
        st.error(f"⚠️ Error al conectar con fuentes: {e}")
        return {}

# --- 2. MOTOR DE PROCESAMIENTO CON ALERTAS ---
def procesar_lista_tickers(lista_tickers, nombre_mercado, progreso_bar, monitor_text):
    resultados = []
    total = len(lista_tickers)
    
    for i, t in enumerate(lista_tickers):
        try:
            monitor_text.text(f"🔍 Analizando {nombre_mercado}: {t} ({i+1}/{total})")
            tk = yf.Ticker(t)
            
            p = tk.fast_info['last_price']
            info = tk.info
            
            # Lógica V10
            target = info.get('targetMeanPrice')
            eps = info.get('forwardEps')
            pe = info.get('forwardPE', 15)
            ebitda = info.get('ebitda', 0) or 0
            
            p_justo = target if target else (pe * eps if eps else p)
            margen = ((p_justo - p) / p) * 100 if p else 0
            
            # --- MEJORA: CÁLCULO DE NIVELES V10 ---
            n1 = round(p * 0.96, 2)  # -4% aprox
            n2 = round(p * 0.92, 2)  # -8% aprox
            
            # Filtro Semáforo
            if margen > 15 and ebitda > 0:
                estado = "🟢 COMPRA CLARA"
                
                # --- SISTEMA DE ALERTA TELEGRAM ---
                distancia_n1 = ((p - n1) / n1) * 100
                if p <= n1:
                    msg = (f"🚨 *ALERTA V10: {t} EN ZONA DE CAZA*\n\n"
                           f"💰 Precio: ${p:.2f}\n"
                           f"🎯 Nivel 1: ${n1:.2f}\n"
                           f"📈 Margen Seg: {margen:.1f}%\n"
                           f"📊 EBITDA: {ebitda:,} ✅ Sólido\n"
                           f"🏢 Mercado: {nombre_mercado}")
                    enviar_telegram(msg)
                elif distancia_n1 <= 1.5:
                    msg = (f"🟡 *VIGILANCIA: {t} CERCA DE NIVEL 1*\n"
                           f"Precio actual ${p:.2f} está a {distancia_n1:.1f}% del objetivo.")
                    enviar_telegram(msg)
            
            elif margen > 5 and ebitda > 0:
                estado = "🟡 VIGILAR"
            else:
                continue 
                
            resultados.append({
                "Mercado": nombre_mercado,
                "Ticker": t,
                "Estado": estado,
                "Precio": round(p, 2),
                "Margen %": round(margen, 1),
                "Sector": info.get('sector', 'N/A'),
                "Nivel 1": n1
            })
        except:
            continue
        progreso_bar.progress((i + 1) / total)
    
    return resultados

# --- 3. INTERFAZ (EL RESTO DEL CÓDIGO SE MANTIENE IGUAL) ---
tab1, tab2, tab3 = st.tabs(["🎯 RADAR SEMÁFORO", "🔍 AUDITORIA", "🌡️ SENTIMIENTO"])

with tab1:
    st.subheader("Radar de Oportunidades Segmentado")
    universo = obtener_universo_autonomo()
    
    if universo:
        c1, c2 = st.columns(2)
        with c1:
            mercado_selec = st.selectbox("Mercado Específico:", list(universo.keys()))
            btn_solo = st.button(f"🚀 Escanear {mercado_selec}")
        with c2:
            st.write("Análisis de Todo el Universo")
            btn_global = st.button("🌍 EJECUTAR ESCANEO GLOBAL")

        df_final = pd.DataFrame()

        if btn_solo:
            progreso = st.progress(0)
            monitor = st.empty()
            datos = procesar_lista_tickers(universo[mercado_selec], mercado_selec, progreso, monitor)
            df_final = pd.DataFrame(datos)
            monitor.empty()

        elif btn_global:
            todas_oportunidades = []
            progreso = st.progress(0)
            monitor = st.empty()
            for m_nombre, m_tickers in universo.items():
                res_m = procesar_lista_tickers(m_tickers, m_nombre, progreso, monitor)
                todas_oportunidades.extend(res_m)
            df_final = pd.DataFrame(todas_oportunidades)
            monitor.empty()

        if not df_final.empty:
            df_final = df_final.drop_duplicates(subset=['Ticker'], keep='first')
            st.success(f"✅ Se encontraron {len(df_final)} oportunidades únicas.")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Oportunidades_V10')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Descargar Reporte en Excel",
                data=excel_data,
                file_name='Reporte_V10_Final.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            df_final.index = range(1, len(df_final) + 1)
            st.dataframe(df_final.sort_values(by=["Mercado", "Margen %"], ascending=[True, False]), use_container_width=True)

with tab2:
    st.subheader("Auditoría de Activo")
    tk_in = st.text_input("Ticker:", "MSFT").upper()
    if tk_in:
        acc = yf.Ticker(tk_in)
        h = acc.history(period="1y")
        if not h.empty:
            fig = go.Figure(data=[go.Candlestick(x=h.index, open=h['Open'], high=h['High'], low=h['Low'], close=h['Close'])])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Sentimiento del Mercado")
    spy_h = yf.Ticker("SPY").history(period="1mo")
    rsi_val = ta.rsi(spy_h['Close'], length=14).iloc[-1]
    st.metric("RSI SPY", f"{rsi_val:.2f}")
    st.info("RSI < 30: Pánico | RSI > 70: Euforia")
