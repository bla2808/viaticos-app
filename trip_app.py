
import math
from io import BytesIO
from typing import Optional

import pandas as pd
import streamlit as st
from PIL import Image

# =====================
# Utilidades
# =====================
def auto_fit_columns(writer, df, sheet_name):
    """Autoajusta columnas con xlsxwriter."""
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]
    # Ancho minimo por estética
    for idx, col in enumerate(df.columns):
        series = df[col].astype(str)
        max_len = max([len(col)] + series.map(len).tolist())
        # aproximación para ancho
        worksheet.set_column(idx, idx, min(max_len + 2, 60))

def calcular_gasolina_manual(distancia_km_1via: float, km_por_litro: float, precio_litro: float, ida_y_vuelta: bool) -> float:
    """Costo de gasolina calculado manualmente con distancia proporcionada por el usuario."""
    if distancia_km_1via < 0 or km_por_litro <= 0 or precio_litro < 0:
        return 0.0
    distancia_total = distancia_km_1via * (2 if ida_y_vuelta else 1)
    litros = distancia_total / km_por_litro
    return litros * precio_litro

def calcular_casetas_manual(casetas_1via: float, ida_y_vuelta: bool) -> float:
    if casetas_1via < 0:
        return 0.0
    return casetas_1via * (2 if ida_y_vuelta else 1)

# Placeholder para cálculo automático con APIs externas.
# Necesitarás configurar las claves en la barra lateral o en st.secrets.
def obtener_distancia_km_api(origen: str, destino: str, api: str, api_key: Optional[str]) -> Optional[float]:
    """
    Devuelve la distancia en KM usando un proveedor externo.
    Por seguridad, NO hacemos la llamada aquí. Retorna None si falta clave.
    Proveedor sugerido:
      - OpenRouteService (https://openrouteservice.org) -> api='ors' (gratuito, hasta 2.500/día)
      - Google Maps Distance Matrix -> api='gmaps'
    Implementa la llamada en tu entorno backend según tu política de claves.
    """
    if not api_key:
        return None
    # Aquí dejaríamos el esqueleto de la llamada. En Streamlit Cloud
    # puedes hacerlo si guardas la clave en st.secrets["ORS_API_KEY"] o similar.
    # Ejemplo de pseudocódigo (NO ejecutable sin requests):
    # import requests
    # if api == "ors":
    #     url = "https://api.openrouteservice.org/v2/directions/driving-car"
    #     resp = requests.get(url, params={"api_key": api_key, "start": ..., "end": ...})
    #     distancia_m = resp.json()["features"][0]["properties"]["summary"]["distance"]
    #     return distancia_m / 1000.0
    return None

# =====================
# UI
# =====================
st.set_page_config(page_title="Calculadora de Viáticos", page_icon="💼", layout="centered")

# Logo (opcional)
try:
    logo = Image.open("logo.png")
    st.image(logo, width=220)
except Exception:
    pass

st.title("💼 Calculadora de Viáticos")

with st.sidebar:
    st.subheader("⚙️ Opciones avanzadas")
    st.caption("Si deseas **cálculo automático** de distancia, añade tu API key.")
    proveedor_api = st.selectbox("Proveedor de mapas", ["Ninguno (manual)", "OpenRouteService (ORS)", "Google Maps"], index=0)
    if proveedor_api == "OpenRouteService (ORS)":
        api_key_input = st.text_input("ORS API Key", value=st.secrets.get("ORS_API_KEY", ""))
        api_provider_code = "ors"
    elif proveedor_api == "Google Maps":
        api_key_input = st.text_input("Google Maps API Key", value=st.secrets.get("GMAPS_API_KEY", ""))
        api_provider_code = "gmaps"
    else:
        api_key_input = ""
        api_provider_code = ""

# ---------- Parámetros base ----------
colA, colB = st.columns(2)
with colA:
    dias = st.number_input("Días de viaje", min_value=1, value=1, step=1)
    alim_dia = st.number_input("Alimentación por día ($)", min_value=0.0, value=0.0, step=10.0)
    personas = st.number_input("Número de personas", min_value=1, value=1, step=1)

with colB:
    hosp_dia = st.number_input("Hospedaje por día ($)", min_value=0.0, value=0.0, step=10.0)
    personas_x_hab = st.number_input("Personas por habitación", min_value=1, value=1, step=1)

rooms = math.ceil(personas / personas_x_hab)

st.markdown("---")
st.subheader("🚗 Transporte")

medio = st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"])

ida_vuelta = st.checkbox("Calcular **ida y vuelta**", value=True)

transporte_total = 0.0
detalle_transporte = {}

if medio == "Auto":
    submodo = st.radio("Modo de cálculo", ["Manual", "Automático (API)"], horizontal=True)

    km_litro = st.number_input("Rendimiento del vehículo (km/L)", min_value=0.1, value=12.0, step=0.1)
    precio_litro = st.number_input("Precio gasolina ($/L)", min_value=0.0, value=25.0, step=0.5)

    if submodo == "Manual":
        distancia_km_1via = st.number_input("Distancia (km) **una vía**", min_value=0.0, value=0.0, step=10.0)
        casetas_1via = st.number_input("Casetas (costo) **una vía** ($)", min_value=0.0, value=0.0, step=10.0)

        costo_gas = calcular_gasolina_manual(distancia_km_1via, km_litro, precio_litro, ida_vuelta)
        costo_casetas = calcular_casetas_manual(casetas_1via, ida_vuelta)

        transporte_total = costo_gas + costo_casetas
        detalle_transporte.update({
            "Distancia (km una vía)": distancia_km_1via,
            "Gasolina ($)": round(costo_gas, 2),
            "Casetas ($)": round(costo_casetas, 2)
        })

    else:  # Automático (API)
        col1, col2 = st.columns(2)
        with col1:
            origen = st.text_input("Ciudad de origen", value="")
        with col2:
            destino = st.text_input("Ciudad de destino", value="")

        distancia_km = None
        if st.button("🔎 Obtener distancia automáticamente"):
            distancia_km = obtener_distancia_km_api(origen, destino, api_provider_code, api_key_input)
            if distancia_km is None:
                st.warning("No se pudo obtener la distancia. Verifica que agregaste una API Key válida.")
            else:
                st.success(f"Distancia aproximada: {distancia_km:,.1f} km (una vía)")

        # Permite sobreescribir/editar manualmente si el usuario la conoce
        distancia_km_1via = st.number_input("Distancia detectada/ajustada (km) **una vía**", min_value=0.0, value=float(distancia_km or 0.0), step=10.0)
        casetas_1via = st.number_input("Casetas (costo) **una vía** ($)", min_value=0.0, value=0.0, step=10.0)

        costo_gas = calcular_gasolina_manual(distancia_km_1via, km_litro, precio_litro, ida_vuelta)
        costo_casetas = calcular_casetas_manual(casetas_1via, ida_vuelta)

        transporte_total = costo_gas + costo_casetas
        detalle_transporte.update({
            "Distancia (km una vía)": distancia_km_1via,
            "Gasolina ($)": round(costo_gas, 2),
            "Casetas ($)": round(costo_casetas, 2)
        })

elif medio == "Avión":
    boleto = st.number_input("Costo del boleto (ida **una vía**) ($)", min_value=0.0, value=0.0, step=50.0)
    transporte_total = boleto * (2 if ida_vuelta else 1) * personas
    detalle_transporte.update({
        "Boleto por persona (una vía) ($)": boleto,
        "Personas": personas,
    })

else:  # Otro
    transporte_total = st.number_input("Transporte total ($)", min_value=0.0, value=0.0, step=10.0)

otros = st.number_input("Otros gastos ($)", min_value=0.0, value=0.0, step=10.0)

# ---------- Cálculos ----------
hosp_total = dias * hosp_dia * rooms
alim_total = dias * alim_dia * personas
total_viaticos = hosp_total + alim_total + transporte_total + otros

st.markdown("---")
st.subheader("🧾 Resumen")
col1, col2 = st.columns(2)
with col1:
    st.metric("Habitaciones", rooms)
    st.metric("Hospedaje total", f"${hosp_total:,.2f}")
    st.metric("Alimentación total", f"${alim_total:,.2f}")
with col2:
    st.metric("Transporte total", f"${transporte_total:,.2f}")
    st.metric("Otros", f"${otros:,.2f}")
st.success(f"**Total de viáticos: ${total_viaticos:,.2f}**")

# ---------- Excel ----------
if st.button("🗎 Descargar Excel"):
    data = {
        "Días de viaje": [dias],
        "Personas": [personas],
        "Personas por habitación": [personas_x_hab],
        "Habitaciones": [rooms],
        "Hospedaje por día": [hosp_dia],
        "Hospedaje total": [round(hosp_total, 2)],
        "Alimentación por día": [alim_dia],
        "Alimentación total": [round(alim_total, 2)],
        "Medio de transporte": [medio],
        "Transporte total": [round(transporte_total, 2)],
        "Otros": [round(otros, 2)],
        "Total Viáticos": [round(total_viaticos, 2)]
    }
    # Agregar detalles de transporte si aplica
    for k, v in detalle_transporte.items():
        data[f"Transporte - {k}"] = [v]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        auto_fit_columns(writer, df, "Viaticos")
        writer.close()
    st.download_button(
        label="Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------- Reset ----------
if st.button("↺ Reiniciar formulario"):
    st.session_state.clear()
    st.rerun()
