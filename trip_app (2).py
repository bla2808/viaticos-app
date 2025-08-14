
import math
from io import BytesIO
import json

import pandas as pd
import streamlit as st

# ---------- Utilidades ----------
def fetch_distance_google(origin_city: str, dest_city: str, api_key: str):
    """
    Devuelve (distancia_km, error_msg).
    - distancia_km: float | None
    - error_msg: str | None
    Maneja falta de 'requests' o errores de API sin romper la app.
    """
    if not api_key or not origin_city or not dest_city:
        return None, "Falta API key o ciudades."

    try:
        import requests  # import local para no requerirlo si no se usa
    except Exception:
        return None, "El módulo 'requests' no está instalado. Agrégalo a requirements.txt si deseas usar la búsqueda automática."

    try:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin_city,
            "destinations": dest_city,
            "units": "metric",
            "key": api_key,
        }
        resp = requests.get(url, params=params, timeout=12)
        data = resp.json()
        if data.get("status") != "OK":
            return None, f"Respuesta API: {data.get('status', 'desconocido')}"
        rows = data.get("rows", [])
        if not rows or not rows[0].get("elements"):
            return None, "Sin elementos en la respuesta."
        elem = rows[0]["elements"][0]
        if elem.get("status") != "OK":
            return None, f"Estatus elemento: {elem.get('status')}"
        meters = elem["distance"]["value"]
        return meters / 1000.0, None
    except Exception as e:
        return None, f"Error consultando API: {e}"


def autosize_columns(writer, df, sheet_name):
    """Ajusta el ancho de columnas en XlsxWriter según el contenido."""
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]

    for idx, col in enumerate(df.columns):
        # ancho por nombre de columna
        max_len = len(str(col))
        # ancho por celdas
        for val in df[col].astype(str):
            max_len = max(max_len, len(val))
        # margen
        width = max_len + 2
        worksheet.set_column(idx, idx, width)


def reset_form():
    """Borra todo el session_state y recarga la app."""
    st.session_state.clear()
    st.rerun()


# ---------- UI ----------
# Logo (si existe en el repo)
try:
    st.image("logo.png", width=220)
except Exception:
    pass

st.title("💼 Calculadora de Viáticos")

# ---- Parámetros básicos ----
colA, colB = st.columns(2)
with colA:
    dias = st.number_input("Días de viaje", min_value=1, value=1, step=1)
    personas = st.number_input("Número de personas", min_value=1, value=1, step=1)
    personas_por_hab = st.number_input("Personas por habitación", min_value=1, value=1, step=1)
with colB:
    hospedaje_dia = st.number_input("Hospedaje por habitación por día ($)", min_value=0.0, value=0.0, step=100.0)
    alimentacion_dia = st.number_input("Alimentación por día por persona ($)", min_value=0.0, value=0.0, step=50.0)

otros_gastos = st.number_input("Otros gastos ($)", min_value=0.0, value=0.0, step=50.0)

# ---- Transporte ----
st.subheader("Transporte")
medio = st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"])

ida_vuelta = st.checkbox("Calcular ida y vuelta", value=True)

transporte_manual = 0.0  # suma de campos manuales en cualquier medio
transporte_auto = 0.0
transporte_avion = 0.0

if medio == "Auto":
    c1, c2, c3 = st.columns(3)
    with c1:
        precio_gas = st.number_input("Precio gasolina ($/L)", min_value=0.0, value=25.0, step=0.5)
    with c2:
        rendimiento = st.number_input("Rendimiento promedio (km/L)", min_value=0.1, value=12.0, step=0.5)
    with c3:
        casetas_un_via = st.number_input("Casetas (costo) una vía ($)", min_value=0.0, value=0.0, step=50.0)

    st.markdown("**Distancia**")
    colD, colE = st.columns(2)
    with colD:
        origen = st.text_input("Ciudad de origen", value="", placeholder="Ej. CDMX")
        destino = st.text_input("Ciudad de destino", value="", placeholder="Ej. Querétaro")
    with colE:
        google_key = st.text_input("API Key de Google Maps (opcional)", type="password", help="Para cálculo automático de distancia.")
        auto_km = st.number_input("Distancia detectada/ajustada (km) una vía", min_value=0.0, value=0.0, step=10.0)

    if st.button("🔎 Obtener distancia automáticamente"):
        km, err = fetch_distance_google(origen, destino, google_key)
        if km is not None:
            st.success(f"Distancia estimada: {km:,.1f} km (una vía). Ajusta si lo deseas.")
            # Guardar en session para sugerir al usuario; evitamos escribir en widgets directamente
            st.session_state["sugerido_km"] = km
        else:
            st.warning(f"No se pudo obtener la distancia. {err or ''}")

    # Mostrar sugerencia si existe
    if "sugerido_km" in st.session_state and st.session_state["sugerido_km"] > 0 and auto_km == 0:
        st.info(f"Sugerencia de distancia una vía: {st.session_state['sugerido_km']:,.1f} km. "
                f"Puedes colocarla manualmente en el campo de distancia.")

    factor_viaje = 2 if ida_vuelta else 1
    litros = (auto_km * factor_viaje) / max(rendimiento, 0.0001)
    gasolina_cost = litros * precio_gas
    casetas_cost = casetas_un_via * factor_viaje
    transporte_auto = gasolina_cost + casetas_cost

    st.caption(f"Estimación gasolina: {litros:,.1f} L → ${gasolina_cost:,.2f} | "
               f"Casetas: ${casetas_cost:,.2f} | **Transporte auto total: ${transporte_auto:,.2f}**")

elif medio == "Avión":
    col1, col2 = st.columns(2)
    with col1:
        costo_boleto_un_via = st.number_input("Costo de boleto (una vía, por persona) $", min_value=0.0, value=0.0, step=100.0)
    with col2:
        transporte_manual = st.number_input("Otros costos de transporte ($)", min_value=0.0, value=0.0, step=50.0)

    factor_viaje = 2 if ida_vuelta else 1
    transporte_avion = costo_boleto_un_via * factor_viaje * personas + transporte_manual
    st.caption(f"**Transporte avión total: ${transporte_avion:,.2f}**")

else:
    transporte_manual = st.number_input("Transporte total ($)", min_value=0.0, value=0.0, step=50.0)

# ---- Cálculo ----
if st.button("Calcular viáticos"):
    # habitaciones necesarias
    habitaciones = math.ceil(personas / max(personas_por_hab, 1))
    hospedaje_total_dia = hospedaje_dia * habitaciones
    alimentacion_total_dia = alimentacion_dia * personas

    transporte_total = transporte_manual
    if medio == "Auto":
        transporte_total += transporte_auto
    elif medio == "Avión":
        transporte_total += transporte_avion

    total = dias * (hospedaje_total_dia + alimentacion_total_dia) + transporte_total + otros_gastos

    st.success(f"**Total de viáticos: ${total:,.2f}**")

    # ---- Armar DataFrame para Excel ----
    resumen = {
        "Días de viaje": [dias],
        "Personas": [personas],
        "Personas por habitación": [personas_por_hab],
        "Habitaciones": [habitaciones],
        "Hospedaje por habitación/día": [hospedaje_dia],
        "Hospedaje total/día": [hospedaje_total_dia],
        "Alimentación por persona/día": [alimentacion_dia],
        "Alimentación total/día": [alimentacion_total_dia],
        "Medio de transporte": [medio],
        "Ida y vuelta": ["Sí" if ida_vuelta else "No"],
        "Transporte total": [transporte_total],
        "Otros gastos": [otros_gastos],
        "Total viáticos": [total],
    }

    # Extras según medio
    if medio == "Auto":
        resumen.update({
            "Precio gasolina ($/L)": [precio_gas],
            "Rendimiento (km/L)": [rendimiento],
            "Distancia una vía (km)": [auto_km],
            "Casetas una vía ($)": [casetas_un_via],
        })
    elif medio == "Avión":
        resumen.update({
            "Costo boleto una vía ($)": [costo_boleto_un_via],
        })

    df = pd.DataFrame(resumen)

    # ---- Generar Excel con auto-ajuste ----
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        autosize_columns(writer, df, "Viaticos")

    st.download_button(
        label="🗎 Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

st.button("Reiniciar formulario", on_click=reset_form)
