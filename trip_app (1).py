
import json
import math
from io import BytesIO
from urllib import request, parse, error

import pandas as pd
import streamlit as st
from PIL import Image


def _http_get_json(url: str, headers: dict | None = None):
    req = request.Request(url, headers=headers or {})
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _http_post_json(url: str, body: dict, headers: dict | None = None):
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers=headers or {}, method="POST")
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def geocode_ors(api_key: str, text: str):
    q = parse.urlencode({"api_key": api_key, "text": text, "size": 1})
    url = f"https://api.openrouteservice.org/geocode/search?{q}"
    js = _http_get_json(url)
    feats = js.get("features", [])
    if not feats:
        return None
    coords = feats[0]["geometry"]["coordinates"]
    return float(coords[0]), float(coords[1])

def driving_distance_km_ors(api_key: str, origin_text: str, dest_text: str):
    o = geocode_ors(api_key, origin_text)
    d = geocode_ors(api_key, dest_text)
    if not o or not d:
        return None
    url = f"https://api.openrouteservice.org/v2/directions/driving-car?api_key={api_key}"
    body = {"coordinates": [[o[0], o[1]], [d[0], d[1]]]}
    headers = {"Content-Type": "application/json"}
    js = _http_post_json(url, body, headers)
    routes = js.get("routes", [])
    if not routes:
        return None
    meters = routes[0]["summary"]["distance"]
    return float(meters) / 1000.0

st.set_page_config(page_title="Calculadora de Viáticos", page_icon="💼", layout="centered")

HAS_LOGO = False
try:
    logo = Image.open("logo.png")
    st.image(logo, width=220)
    HAS_LOGO = True
except Exception:
    pass

st.title("💼 Calculadora de Viáticos")

def init_key(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_key("dias", 1)
init_key("hospedaje", 0.0)
init_key("alimentacion", 0.0)
init_key("personas", 1)
init_key("personas_por_hab", 1)
init_key("precio_gasolina", 25.0)
init_key("km_l", 12.0)
init_key("origen", "")
init_key("destino", "")
init_key("distancia_km", 0.0)
init_key("casetas_unavia", 0.0)
init_key("ida_vuelta", True)
init_key("extra_transporte", 0.0)

st.subheader("Parámetros de viaje")

col1, col2 = st.columns(2)
with col1:
    st.number_input("Días de viaje", min_value=1, key="dias")
    st.number_input("Hospedaje por día ($) por habitación", min_value=0.0, step=100.0, key="hospedaje")
    st.number_input("Alimentación por día ($) por persona", min_value=0.0, step=50.0, key="alimentacion")
    st.number_input("Personas", min_value=1, step=1, key="personas")
    st.number_input("Personas por habitación", min_value=1, step=1, key="personas_por_hab")

with col2:
    st.number_input("Precio gasolina ($/L)", min_value=0.0, step=0.5, key="precio_gasolina")
    st.number_input("Rendimiento del vehículo (km/L)", min_value=0.1, step=0.5, key="km_l")
    st.text_input("Ciudad de origen", key="origen")
    st.text_input("Ciudad de destino", key="destino")

if st.button("🔎 Obtener distancia automáticamente"):
    api_key = st.secrets.get("ORS_API_KEY", "")
    if not api_key:
        st.warning("No se encontró `ORS_API_KEY` en *Secrets*. Ingresa tu API key en **Manage app → Settings → Secrets**.")
    else:
        try:
            dist_km = driving_distance_km_ors(api_key, st.session_state.origen.strip(), st.session_state.destino.strip())
            if dist_km is None:
                st.warning("No se pudo obtener la distancia. Revisa los nombres de las ciudades o tu API Key.")
            else:
                st.session_state.distancia_km = round(dist_km, 1)
                st.success(f"Distancia detectada (una vía): {st.session_state.distancia_km:,.1f} km")
        except error.HTTPError as e:
            st.warning(f"No se pudo obtener la distancia (HTTP {e.code}). Verifica la API Key y vuelve a intentar.")
        except Exception:
            st.warning("No se pudo obtener la distancia. Intenta de nuevo o ingresa la distancia manualmente.")

col3, col4 = st.columns(2)
with col3:
    st.number_input("Distancia detectada/ajustada (km) **una vía**", min_value=0.0, step=10.0, key="distancia_km")
with col4:
    st.number_input("Casetas (costo) **una vía** ($)", min_value=0.0, step=50.0, key="casetas_unavia")

st.checkbox("Calcular **ida y vuelta**", key="ida_vuelta")
st.number_input("Otros transportes / extras ($)", min_value=0.0, step=50.0, key="extra_transporte")

st.markdown("---")

habitaciones = max(1, math.ceil(st.session_state.personas / st.session_state.personas_por_hab))

hospedaje_total = st.session_state.dias * st.session_state.hospedaje * habitaciones
alimentacion_total = st.session_state.dias * st.session_state.alimentacion * st.session_state.personas

dist_total_km = st.session_state.distancia_km * (2 if st.session_state.ida_vuelta else 1)

litros = (dist_total_km / st.session_state.km_l) if st.session_state.km_l > 0 else 0.0
gasolina_total = litros * st.session_state.precio_gasolina

casetas_total = st.session_state.casetas_unavia * (2 if st.session_state.ida_vuelta else 1)

transporte_total = gasolina_total + casetas_total + st.session_state.extra_transporte

total_viaticos = hospedaje_total + alimentacion_total + transporte_total

st.subheader("Resumen")
cA, cB, cC = st.columns(3)
cA.metric("Habitaciones", f"{habitaciones}")
cB.metric("Distancia total (km)", f"{dist_total_km:,.1f}")
cC.metric("Litros estimados", f"{litros:,.1f} L")

c1, c2, c3 = st.columns(3)
c1.metric("Hospedaje total", f"${hospedaje_total:,.2f}")
c2.metric("Alimentación total", f"${alimentacion_total:,.2f}")
c3.metric("Transporte total", f"${transporte_total:,.2f}")

st.success(f"**Total de viáticos: ${total_viaticos:,.2f}**")

def auto_fit_columns(worksheet, dataframe):
    for idx, col in enumerate(dataframe.columns):
        series = dataframe[col].astype(str)
        max_len = max(len(str(col)), series.map(len).max())
        worksheet.set_column(idx, idx, min(max_len + 2, 60))

if st.button("🗎 Descargar resultado en Excel"):
    data = {
        "Días de viaje": [st.session_state.dias],
        "Personas": [st.session_state.personas],
        "Personas por habitación": [st.session_state.personas_por_hab],
        "Habitaciones": [habitaciones],
        "Hospedaje por día (hab)": [st.session_state.hospedaje],
        "Hospedaje total": [hospedaje_total],
        "Alimentación por día (pers)": [st.session_state.alimentacion],
        "Alimentación total": [alimentacion_total],
        "Precio gasolina ($/L)": [st.session_state.precio_gasolina],
        "Rendimiento (km/L)": [st.session_state.km_l],
        "Origen": [st.session_state.origen],
        "Destino": [st.session_state.destino],
        "Distancia una vía (km)": [st.session_state.distancia_km],
        "Ida y vuelta": ["Sí" if st.session_state.ida_vuelta else "No"],
        "Distancia total (km)": [dist_total_km],
        "Litros estimados": [litros],
        "Casetas una vía ($)": [st.session_state.casetas_unavia],
        "Casetas total ($)": [casetas_total],
        "Otros transportes ($)": [st.session_state.extra_transporte],
        "Gasolina total ($)": [gasolina_total],
        "Transporte total ($)": [transporte_total],
        "TOTAL VIÁTICOS ($)": [total_viaticos],
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        startrow = 6
        df.to_excel(writer, index=False, sheet_name="Viaticos", startrow=startrow)
        ws = writer.sheets["Viaticos"]
        book = writer.book

        title_fmt = book.add_format({
            "bold": True, "font_size": 20, "align": "left", "valign": "vcenter"
        })
        subtitle_fmt = book.add_format({
            "italic": True, "font_size": 10, "font_color": "#555555"
        })
        header_fmt = book.add_format({
            "bold": True, "bg_color": "#F2F2F2", "border": 1
        })

        try:
            ws.insert_image("A1", "logo.png", {"x_scale": 0.4, "y_scale": 0.4})
        except Exception:
            pass
        ws.merge_range("C1:H2", "Reporte de Viáticos", title_fmt)
        ws.write("C3", "Generado por Calculadora de Viáticos", subtitle_fmt)

        for col_num in range(len(df.columns)):
            ws.write(startrow, col_num, df.columns[col_num], header_fmt)

        auto_fit_columns(ws, df)

    st.download_button(
        label="Descargar Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if st.button("Reiniciar formulario"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_rerun()
