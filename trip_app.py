import math
import pandas as pd
from io import BytesIO
import streamlit as st
from PIL import Image
import requests

# ---------- Utilidades para APIs ----------
def km_from_google_directions(origin: str, destination: str, api_key: str) -> float | None:
    """Obtiene distancia en km usando Google Directions API (primer ruta)."""
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
    """Estimación de casetas usando Tollguru (auto 2 ejes)."""
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
try:
    logo = Image.open("logo.png")
    st.image(logo, width=200)
except Exception:
    st.write("**SEPAC Ingeniería**")  # fallback si no hay logo

st.title("💼 Calculadora de Viáticos")


# ---------- Defaults ----------
defaults = {
    "dias": 1,
    "personas": 1,
    "personas_por_hab": 1,
    "costo_habitacion": 0.0,     # $ por habitación por noche
    "alimentacion": 0.0,         # $ por día por persona
    "transporte": 0.0,           # otros transportes
    "medio": "Auto",
    "boleto": 0.0,               # total boletos
    "otros": 0.0,
    # Auto / Ruta
    "usar_apis": True,
    "demo_mode": False,          # Nuevo: modo demo si no hay keys
    "origen": "Ciudad de México",
    "destino": "",
    "km_litro": 0.0,
    "precio_gasolina": 0.0,
    "distancia_km": 0.0,         # solo ida
    "casetas": 0.0,              # solo ida
    "distancia_km_demo": 220.0,  # valores ejemplo (editables)
    "casetas_demo": 200.0,
    "ida_vuelta": False          # si True, multiplica distancia y casetas por 2
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- Entradas ----------
c1, c2 = st.columns(2)
with c1:
    st.number_input("Días de viaje", min_value=1, key="dias")
    st.number_input("Número de personas", min_value=1, key="personas")
    st.number_input("Personas por habitación", min_value=1, key="personas_por_hab")
with c2:
    st.number_input("Hospedaje por habitación por noche ($)", min_value=0.0, key="costo_habitacion")
    st.number_input("Alimentación por día por persona ($)", min_value=0.0, key="alimentacion")
    st.number_input("Otros transportes ($)", min_value=0.0, key="transporte")

st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"], key="medio")

if st.session_state["medio"] == "Avión":
    st.number_input("Boleto de avión (total) ($)", min_value=0.0, key="boleto")
    # limpiar campos de auto
    st.session_state.update({
        "origen": "Ciudad de México",
        "destino": "",
        "km_litro": 0.0,
        "precio_gasolina": 0.0,
        "distancia_km": 0.0,
        "casetas": 0.0,
        "ida_vuelta": False,
        "demo_mode": False
    })

elif st.session_state["medio"] == "Auto":
    st.checkbox("Calcular ruta y casetas automáticamente (APIs)", key="usar_apis", value=st.session_state.get("usar_apis", True))
    st.checkbox("Calcular ida y vuelta", key="ida_vuelta")
    st.checkbox("Modo demo (sin APIs)", key="demo_mode")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.text_input("Origen", key="origen")
        st.number_input("Km por litro", min_value=0.0, key="km_litro")
    with cc2:
        st.text_input("Destino", key="destino")
        st.number_input("Precio gasolina ($/litro)", min_value=0.0, key="precio_gasolina")

    if st.session_state["demo_mode"]:
        st.number_input("Distancia DEMO (solo ida) km", min_value=0.0, key="distancia_km_demo")
        st.number_input("Casetas DEMO (solo ida) $", min_value=0.0, key="casetas_demo")
    elif not st.session_state["usar_apis"]:
        st.number_input("Distancia (solo ida) en km", min_value=0.0, key="distancia_km")
        st.number_input("Casetas (solo ida) en $", min_value=0.0, key="casetas")
else:
    # limpiar ambos grupos
    st.session_state.update({
        "boleto": 0.0,
        "origen": "Ciudad de México",
        "destino": "",
        "km_litro": 0.0,
        "precio_gasolina": 0.0,
        "distancia_km": 0.0,
        "casetas": 0.0,
        "ida_vuelta": False,
        "demo_mode": False
    })

st.number_input("Otros gastos ($)", min_value=0.0, key="otros")

# ---------- Cálculo ----------
if st.button("Calcular viáticos"):
    # Si es Auto y se pidió usar APIs (y NO está en modo demo)
    if st.session_state["medio"] == "Auto" and st.session_state["usar_apis"] and not st.session_state["demo_mode"]:
        gkey = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        tkey = st.secrets.get("TOLLGURU_API_KEY", "")
        if gkey and st.session_state["origen"] and st.session_state["destino"]:
            km = km_from_google_directions(st.session_state["origen"], st.session_state["destino"], gkey)
            if km is not None:
                st.session_state["distancia_km"] = km  # ida
        if tkey and st.session_state["origen"] and st.session_state["destino"]:
            toll = tolls_from_tollguru(st.session_state["origen"], st.session_state["destino"], tkey)
            if toll is not None:
                st.session_state["casetas"] = toll      # ida

    # Factor ida y vuelta
    factor = 2 if (st.session_state.get("ida_vuelta", False) and st.session_state["medio"] == "Auto") else 1

    # --- Hospedaje por habitación
    habitaciones = math.ceil(st.session_state["personas"] / st.session_state["personas_por_hab"])
    hospedaje_total = st.session_state["dias"] * habitaciones * st.session_state["costo_habitacion"]

    # --- Alimentación por persona
    alimentacion_total = st.session_state["dias"] * st.session_state["alimentacion"] * st.session_state["personas"]

    # --- Distancia/Casetas fuentes (orden de prioridad)
    # 1) Demo -> usa distancia_km_demo y casetas_demo
    # 2) APIs -> distancia_km y casetas (si se obtuvieron)
    # 3) Manual -> distancia_km y casetas (si el usuario los capturó)
    if st.session_state["medio"] == "Auto" and st.session_state["demo_mode"]:
        distancia_ida = st.session_state.get("distancia_km_demo", 0.0)
        casetas_ida = st.session_state.get("casetas_demo", 0.0)
    else:
        distancia_ida = st.session_state.get("distancia_km", 0.0)
        casetas_ida = st.session_state.get("casetas", 0.0)

    distancia_total_km = distancia_ida * factor
    casetas_totales = casetas_ida * factor

    # --- Gasolina (usa distancia total)
    gasolina_total = 0.0
    if (
        st.session_state["medio"] == "Auto"
        and st.session_state["km_litro"] > 0
        and st.session_state["precio_gasolina"] > 0
        and distancia_total_km > 0
    ):
        litros = distancia_total_km / st.session_state["km_litro"]
        gasolina_total = round(litros * st.session_state["precio_gasolina"], 2)

    # --- Total
    total = (
        hospedaje_total +
        alimentacion_total +
        st.session_state["transporte"] +
        st.session_state["boleto"] +
        st.session_state["otros"] +
        gasolina_total +
        casetas_totales
    )

    # ------ Resumen en pantalla
    st.success(f"Total de viáticos: ${total:,.2f}")
    st.info(f"Habitaciones: {habitaciones} | Hospedaje total: ${hospedaje_total:,.2f}")
    if st.session_state["medio"] == "Auto"]:
        tramo = "ida y vuelta" if factor == 2 else "solo ida"
        fuente = "DEMO" if st.session_state.get("demo_mode", False) else ("APIs" if st.session_state.get("usar_apis", False) else "Manual")
        st.info(f"Distancia ({tramo}) [{fuente}]: {distancia_total_km:.1f} km | Gasolina: ${gasolina_total:,.2f} | Casetas: ${casetas_totales:,.2f}")

    # ------ DataFrame detallado
    df = pd.DataFrame([{
        "Días de viaje": st.session_state["dias"],
        "Personas": st.session_state["personas"],
        "Personas por habitación": st.session_state["personas_por_hab"],
        "Habitaciones": habitaciones,
        "Medio de transporte": st.session_state["medio"],
        "Origen": st.session_state.get("origen", ""),
        "Destino": st.session_state.get("destino", ""),
        "Ida y vuelta": "Sí" if factor == 2 else "No",
        "Hospedaje por habitación/noche": st.session_state["costo_habitacion"],
        "Hospedaje total": hospedaje_total,
        "Alimentación por día/persona": st.session_state["alimentacion"],
        "Alimentación total": alimentacion_total,
        "Otros transportes": st.session_state["transporte"],
        "Boleto avión (total)": st.session_state["boleto"],
        "Km por litro": st.session_state.get("km_litro", 0.0),
        "Precio gasolina": st.session_state.get("precio_gasolina", 0.0),
        "Distancia km (total viaje)": distancia_total_km,
        "Gasolina total": gasolina_total,
        "Casetas (total viaje)": casetas_totales,
        "Fuente de ruta": "DEMO" if st.session_state.get("demo_mode", False) else ("APIs" if st.session_state.get("usar_apis", False) else "Manual"),
        "Otros": st.session_state["otros"],
        "TOTAL VIÁTICOS": total
    }])

    # ------ Exportar a Excel con autoajuste y formato
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
            "Precio gasolina", "Gasolina total", "Casetas (total viaje)", "Otros",
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
