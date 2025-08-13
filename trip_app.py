import math
import pandas as pd
from io import BytesIO
import streamlit as st
from PIL import Image
import requests

# ---------- Utilidades opcionales para APIs (fase rutas/casetas) ----------
def km_from_google_directions(origin: str, destination: str, api_key: str) -> float | None:
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "region": "mx",
            "units": "metric",
            "key": api_key,
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("routes"):
            return None
        leg = data["routes"][0]["legs"][0]
        meters = leg["distance"]["value"]
        return round(meters / 1000.0, 1)
    except Exception:
        return None

def tolls_from_tollguru(origin: str, destination: str, api_key: str) -> float | None:
    try:
        url = "https://apis.tollguru.com/toll/v2/complete-route"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "from": origin,
            "to": destination,
            "vehicleType": "2AxlesAuto",
            "source": "google",
            "calculateAlternativeRoutes": False,
            "avoid": {"ferries": True}
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None
        data = resp.json()
        route = data.get("route") or (data.get("routes") or [{}])[0]
        totals = route.get("costs") or route.get("cost", {})
        toll = None
        if isinstance(totals, dict):
            for key in ["toll", "tolls", "cash", "tag", "tagCost", "cashCost", "totalTollCost"]:
                val = totals.get(key)
                if isinstance(val, (int, float)):
                    toll = float(val)
                    break
        if toll is None:
            plazas = route.get("tolls") or []
            acc = 0.0
            for p in plazas:
                v = p.get("cash") or p.get("tag") or p.get("price")
                if isinstance(v, (int, float)):
                    acc += float(v)
            toll = acc if acc > 0 else None
        return round(toll, 2) if toll is not None else None
    except Exception:
        return None

# ---------- Reset seguro al inicio ----------
if st.session_state.get("reset", False):
    st.session_state.clear()
    st.session_state["reset"] = False
    st.rerun()

# ---------- UI base ----------
logo = Image.open("logo.png")
st.image(logo, width=200)
st.title("💼 Calculadora de Viáticos")

# ---------- Defaults ----------
defaults = {
    "dias": 1,
    "personas": 1,
    # Hospedaje por habitación (no por persona)
    "costo_habitacion": 0.0,            # $ por habitación por noche
    "personas_por_hab": 1,              # cuántas personas se alojan en una misma habitación
    "alimentacion": 0.0,                # $ por persona por día
    "transporte": 0.0,                  # otros transportes
    "medio": "Auto",
    "boleto": 0.0,                      # total boletos avión
    "otros": 0.0,
    # Auto / Ruta
    "usar_apis": False,
    "origen": "Ciudad de México",
    "destino": "",
    "km_litro": 0.0,
    "precio_gasolina": 0.0,
    "distancia_km": 0.0,
    "casetas": 0.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- Entradas ----------
col1, col2 = st.columns(2)
with col1:
    st.number_input("Días de viaje", min_value=1, key="dias")
    st.number_input("Número de personas", min_value=1, key="personas")
with col2:
    st.number_input("Personas por habitación", min_value=1, key="personas_por_hab")
    st.number_input("Hospedaje por habitación por noche ($)", min_value=0.0, key="costo_habitacion")

st.number_input("Alimentación por día por persona ($)", min_value=0.0, key="alimentacion")
st.number_input("Otros transportes ($)", min_value=0.0, key="transporte")

st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"], key="medio")

if st.session_state["medio"] == "Avión":
    st.number_input("Boleto de avión (total) ($)", min_value=0.0, key="boleto")
    # limpiar campos de auto
    st.session_state["origen"] = "Ciudad de México"
    st.session_state["destino"] = ""
    st.session_state["km_litro"] = 0.0
    st.session_state["precio_gasolina"] = 0.0
    st.session_state["distancia_km"] = 0.0
    st.session_state["casetas"] = 0.0

elif st.session_state["medio"] == "Auto":
    st.checkbox("Calcular ruta y casetas automáticamente (APIs)", key="usar_apis")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Origen", key="origen")
        st.number_input("Km por litro", min_value=0.0, key="km_litro")
    with c2:
        st.text_input("Destino", key="destino")
        st.number_input("Precio gasolina ($/litro)", min_value=0.0, key="precio_gasolina")

    if not st.session_state["usar_apis"]:
        st.number_input("Distancia total (km)", min_value=0.0, key="distancia_km")
        st.number_input("Casetas ($)", min_value=0.0, key="casetas")
    else:
        # si hay secrets configurados, intentamos cálculo automático al presionar Calcular
        pass

else:
    # limpiar ambos grupos
    st.session_state["boleto"] = 0.0
    st.session_state["origen"] = "Ciudad de México"
    st.session_state["destino"] = ""
    st.session_state["km_litro"] = 0.0
    st.session_state["precio_gasolina"] = 0.0
    st.session_state["distancia_km"] = 0.0
    st.session_state["casetas"] = 0.0

st.number_input("Otros gastos ($)", min_value=0.0, key="otros")

# ---------- Cálculo ----------
if st.button("Calcular viáticos"):
    # Si es Auto y se pidió usar APIs
    if st.session_state["medio"] == "Auto" and st.session_state["usar_apis"]:
        gkey = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        tkey = st.secrets.get("TOLLGURU_API_KEY", "")
        if gkey and st.session_state["origen"] and st.session_state["destino"]:
            km = km_from_google_directions(st.session_state["origen"], st.session_state["destino"], gkey)
            if km is not None:
                st.session_state["distancia_km"] = km
        if tkey and st.session_state["origen"] and st.session_state["destino"]:
            toll = tolls_from_tollguru(st.session_state["origen"], st.session_state["destino"], tkey)
            if toll is not None:
                st.session_state["casetas"] = toll

    # --- Hospedaje por habitación
    # habitaciones = ceil(personas / personas_por_hab)
    habitaciones = math.ceil(st.session_state["personas"] / st.session_state["personas_por_hab"])
    hospedaje_total = st.session_state["dias"] * habitaciones * st.session_state["costo_habitacion"]

    # --- Alimentación por persona
    alimentacion_total = st.session_state["dias"] * st.session_state["alimentacion"] * st.session_state["personas"]

    # --- Gasolina si aplica
    gasolina_total = 0.0
    if st.session_state["medio"] == "Auto" and st.session_state["km_litro"] > 0 and st.session_state["precio_gasolina"] > 0 and st.session_state["distancia_km"] > 0:
        litros = st.session_state["distancia_km"] / st.session_state["km_litro"]
        gasolina_total = round(litros * st.session_state["precio_gasolina"], 2)

    # --- Total
    total = (
        hospedaje_total +
        alimentacion_total +
        st.session_state["transporte"] +
        st.session_state["boleto"] +
        st.session_state["otros"] +
        gasolina_total +
        st.session_state["casetas"]
    )

    # Resumen en pantalla
    st.success(f"Total de viáticos: ${total:,.2f}")
    st.info(f"Habitaciones calculadas: {habitaciones} | Hospedaje total: ${hospedaje_total:,.2f}")
    if st.session_state["medio"] == "Auto":
        st.info(f"Distancia: {st.session_state['distancia_km']:.1f} km | Gasolina: ${gasolina_total:,.2f} | Casetas: ${st.session_state['casetas']:,.2f}")

    # DataFrame detallado
    df = pd.DataFrame([{
        "Días de viaje": st.session_state["dias"],
        "Personas": st.session_state["personas"],
        "Personas por habitación": st.session_state["personas_por_hab"],
        "Habitaciones": habitaciones,
        "Medio de transporte": st.session_state["medio"],
        "Origen": st.session_state.get("origen", ""),
        "Destino": st.session_state.get("destino", ""),
        "Hospedaje por habitación/noche": st.session_state["costo_habitacion"],
        "Hospedaje total": hospedaje_total,
        "Alimentación por día/persona": st.session_state["alimentacion"],
        "Alimentación total": alimentacion_total,
        "Otros transportes": st.session_state["transporte"],
        "Boleto avión (total)": st.session_state["boleto"],
        "Km por litro": st.session_state.get("km_litro", 0.0),
        "Precio gasolina": st.session_state.get("precio_gasolina", 0.0),
        "Distancia km": st.session_state.get("distancia_km", 0.0),
        "Gasolina total": gasolina_total,
        "Casetas": st.session_state.get("casetas", 0.0),
        "Otros": st.session_state["otros"],
        "TOTAL VIÁTICOS": total
    }])

    # Exportar a Excel con autoajuste y formato
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        workbook  = writer.book
        worksheet = writer.sheets["Viaticos"]

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        money_fmt  = workbook.add_format({"num_format": "$#,##0.00"})

        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)

        for col_num, col_name in enumerate(df.columns):
            series_as_str = df[col_name].astype(str)
            max_len_vals = series_as_str.map(len).max() if len(series_as_str) else 0
            max_len = max(max_len_vals, len(col_name)) + 2
            worksheet.set_column(col_num, col_num, max_len)

        cols_moneda = [
            "Hospedaje por habitación/noche", "Hospedaje total",
            "Alimentación por día/persona", "Alimentación total",
            "Otros transportes", "Boleto avión (total)",
            "Precio gasolina", "Gasolina total", "Casetas", "Otros",
            "TOTAL VIÁTICOS"
        ]
        for col_name in cols_moneda:
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name)
                worksheet.set_column(col_idx, col_idx, None, money_fmt)

    st.download_button(
        label="🗎 Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------- Botón de reset ----------
if st.button("Reiniciar formulario"):
    st.session_state["reset"] = True
    st.rerun()
