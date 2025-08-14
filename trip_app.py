
import os
import math
from io import BytesIO
import requests
import pandas as pd
import streamlit as st
from PIL import Image

# ------------ Config -------------
APP_TITLE = "💼 Calculadora de Viáticos"
LOGO_PATH = "logo.png"

DEFAULTS = {
    "dias": 1,
    "hospedaje": 0.0,
    "alimentacion": 0.0,
    "personas": 1,
    "pers_por_hab": 1,
    "medio": "Auto",
    "ida_vuelta": True,
    "precio_gas": 25.0,
    "km_litro": 12.0,
    "distancia_km": 0.0,
    "casetas": 0.0,
    "pais": "Mexico",
    "origen": "",
    "destino": "",
    "otros": 0.0,
    "costo_boleto": 0.0,
    "transporte_otro": 0.0
}

# ------------ Helpers -------------
def ensure_defaults():
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)

def reset_form():
    # Usar update con dict para reestablecer valores de widgets
    st.session_state.update(DEFAULTS)

def km_google_distance(origin, destination, api_key):
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {"origin": origin, "destination": destination, "key": api_key}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("routes"):
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1000.0
    except Exception:
        return None
    return None

def auto_ajustar_columnas(writer, df, sheet_name):
    ws = writer.sheets[sheet_name]
    for idx, col in enumerate(df.columns):
        try:
            max_len = max([len(str(x)) for x in df[col].tolist()] + [len(col)])
        except ValueError:
            max_len = len(col)
        ws.set_column(idx, idx, min(max_len + 2, 60))

# ------------ UI -------------
st.set_page_config(page_title=APP_TITLE, layout="centered")

# Logo
if os.path.exists(LOGO_PATH):
    try:
        st.image(Image.open(LOGO_PATH), width=220)
    except Exception:
        pass

st.title(APP_TITLE)

ensure_defaults()

# Datos base
colA, colB = st.columns(2)
with colA:
    st.number_input("Días de viaje", min_value=1, key="dias")
    st.number_input("Hospedaje por día ($) por habitación", min_value=0.0, step=50.0, key="hospedaje")
    st.number_input("Alimentación por día ($) por persona", min_value=0.0, step=20.0, key="alimentacion")
with colB:
    st.number_input("Número de personas", min_value=1, key="personas")
    st.number_input("Personas por habitación", min_value=1, key="pers_por_hab")
    st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"], key="medio")

st.divider()

# Transporte dinámico
transporte_total = 0.0
detalle_transporte = ""

if st.session_state["medio"] == "Auto":
    st.subheader("Transporte: Auto")
    st.number_input("Precio gasolina ($/L)", min_value=0.0, step=0.5, key="precio_gas")
    st.number_input("Rendimiento del vehículo (km/L)", min_value=0.1, step=0.5, key="km_litro")

    st.text_input("País (solo para referencia)", key="pais")
    st.text_input("Ciudad de origen", key="origen")
    st.text_input("Ciudad de destino", key="destino")

    if st.button("🔎 Obtener distancia automáticamente", use_container_width=True):
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if api_key and st.session_state["origen"] and st.session_state["destino"]:
            km = km_google_distance(st.session_state["origen"], st.session_state["destino"], api_key)
            if km is None:
                st.warning("No se pudo obtener la distancia. Verifica la API Key o las ciudades.")
            else:
                st.session_state["distancia_km"] = round(km, 2)
                st.success(f"Distancia detectada: {km:.2f} km (una vía). Ajusta si es necesario.")
        else:
            st.warning("Agrega tu GOOGLE_MAPS_API_KEY como variable de entorno en Streamlit Cloud y completa origen/destino.")

    st.number_input("Distancia detectada/ajustada (km) una vía", min_value=0.0, key="distancia_km")
    st.number_input("Casetas (costo) una vía ($)", min_value=0.0, step=10.0, key="casetas")
    st.toggle("Calcular ida y vuelta", key="ida_vuelta")

    factor = 2 if st.session_state["ida_vuelta"] else 1
    km_totales = st.session_state["distancia_km"] * factor
    casetas_totales = st.session_state["casetas"] * factor

    litros = km_totales / st.session_state["km_litro"] if st.session_state["km_litro"] > 0 else 0.0
    gasolina = litros * st.session_state["precio_gas"]
    transporte_total = gasolina + casetas_totales
    detalle_transporte = f"Auto: {km_totales:.0f} km, {litros:.1f} L x ${st.session_state['precio_gas']:.2f} + casetas ${casetas_totales:.2f}"

elif st.session_state["medio"] == "Avión":
    st.subheader("Transporte: Avión")
    st.number_input("Costo de boleto por persona ($) una vía", min_value=0.0, step=100.0, key="costo_boleto")
    st.toggle("Calcular ida y vuelta", key="ida_vuelta")
    factor = 2 if st.session_state["ida_vuelta"] else 1
    transporte_total = st.session_state["costo_boleto"] * st.session_state["personas"] * factor
    detalle_transporte = f"Avión: ${st.session_state['costo_boleto']:.2f} x {st.session_state['personas']} persona(s) x {factor} vía(s)"

else:
    st.subheader("Transporte: Otro")
    st.number_input("Transporte total ($)", min_value=0.0, step=50.0, key="transporte_otro")
    transporte_total = st.session_state["transporte_otro"]
    detalle_transporte = "Otro"

st.divider()
st.number_input("Otros gastos ($)", min_value=0.0, step=50.0, key="otros")

# Cálculos principales
rooms = math.ceil(st.session_state["personas"] / st.session_state["pers_por_hab"]) if st.session_state["pers_por_hab"] > 0 else st.session_state["personas"]
hotel = st.session_state["dias"] * st.session_state["hospedaje"] * rooms
alimentos = st.session_state["dias"] * st.session_state["alimentacion"] * st.session_state["personas"]
total_viaticos = hotel + alimentos + transporte_total + st.session_state["otros"]

if st.button("Calcular viáticos", type="primary", use_container_width=True):
    st.success(f"Total de viáticos: ${total_viaticos:,.2f}")

    df = pd.DataFrame([{
        "Días de viaje": st.session_state["dias"],
        "Personas": st.session_state["personas"],
        "Personas por habitación": st.session_state["pers_por_hab"],
        "Habitaciones (calc)": rooms,
        "Hospedaje por día (hab)": st.session_state["hospedaje"],
        "Alimentación por día (persona)": st.session_state["alimentacion"],
        "Hotel total": round(hotel, 2),
        "Alimentos total": round(alimentos, 2),
        "Medio transporte": st.session_state["medio"],
        "Detalle transporte": detalle_transporte,
        "Transporte total": round(transporte_total, 2),
        "Otros": round(st.session_state["otros"], 2),
        "TOTAL VIÁTICOS": round(total_viaticos, 2)
    }])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        auto_ajustar_columnas(writer, df, "Viaticos")

    st.download_button(
        "🗎 Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# Botón reset (callback) - evita conflictos de estado con widgets
st.button("Reiniciar formulario", type="secondary", on_click=reset_form, use_container_width=True)
