import math
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image


# -----------------------------
# Configuración y recursos
# -----------------------------
st.set_page_config(page_title="Calculadora de Viáticos", page_icon="💼")

# Logo (asegúrate de tener logo.png en el repo)
try:
    logo = Image.open("logo.png")
    st.image(logo, width=200)
except Exception:
    pass

st.title("💼 Calculadora de Viáticos")


# -----------------------------
# Defaults y reset
# -----------------------------
DEFAULTS = {
    "dias": 1,
    "hospedaje": 0.0,
    "alimentacion": 0.0,
    "personas": 1,
    "por_habitacion": 1,
    "medio": "Auto",              # Auto / Avión / Otro
    # Auto:
    "km_l": 12.0,
    "precio_gas": 24.0,           # MXN por litro
    "distancia_km": 0.0,          # una vía
    "peajes": 0.0,                # una vía
    "ida_vuelta": True,
    # Avión:
    "boleto": 0.0,
    # Otro:
    "transporte_manual": 0.0,
    # Extra:
    "otros": 0.0,
}

def ensure_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_form():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()

ensure_defaults()


# -----------------------------
# Entradas básicas
# -----------------------------
colA, colB = st.columns(2)
with colA:
    st.number_input("Días de viaje", min_value=1, key="dias")
    st.number_input("Hospedaje por día ($)", min_value=0.0, step=0.1, key="hospedaje")
    st.number_input("Alimentación por día ($)", min_value=0.0, step=0.1, key="alimentacion")
with colB:
    st.number_input("Número de personas", min_value=1, key="personas")
    st.number_input("Personas por habitación", min_value=1, key="por_habitacion")
    st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"], key="medio")


# -----------------------------
# Entradas según medio
# -----------------------------
transporte_calculado = 0.0
detalle_transporte = ""

if st.session_state["medio"] == "Auto":
    st.subheader("Transporte: Auto")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("Rendimiento (km/L)", min_value=0.1, step=0.1, key="km_l")
    with c2:
        st.number_input("Precio gasolina ($/L)", min_value=0.0, step=0.1, key="precio_gas")
    with c3:
        st.number_input("Distancia (km) una vía", min_value=0.0, step=1.0, key="distancia_km")

    c4, c5 = st.columns(2)
    with c4:
        st.number_input("Casetas / peajes ($) una vía", min_value=0.0, step=1.0, key="peajes")
    with c5:
        st.checkbox("Calcular ida y vuelta", key="ida_vuelta")

    factor_viaje = 2.0 if st.session_state["ida_vuelta"] else 1.0
    distancia_total = st.session_state["distancia_km"] * factor_viaje
    peajes_total = st.session_state["peajes"] * factor_viaje

    litros = distancia_total / st.session_state["km_l"] if st.session_state["km_l"] > 0 else 0.0
    gasolina_total = litros * st.session_state["precio_gas"]
    transporte_calculado = gasolina_total + peajes_total

    detalle_transporte = (
        f"Auto: Dist. total = {distancia_total:,.0f} km, "
        f"Gasolina = ${gasolina_total:,.2f}, Casetas = ${peajes_total:,.2f}"
    )

elif st.session_state["medio"] == "Avión":
    st.subheader("Transporte: Avión")
    st.number_input("Costo de boleto ($)", min_value=0.0, step=1.0, key="boleto")
    transporte_calculado = st.session_state["boleto"]
    detalle_transporte = f"Avión: Boleto = ${transporte_calculado:,.2f}"

else:  # Otro
    st.subheader("Transporte: Otro (monto manual)")
    st.number_input("Transporte total ($)", min_value=0.0, step=1.0, key="transporte_manual")
    transporte_calculado = st.session_state["transporte_manual"]
    detalle_transporte = f"Otro: Transporte = ${transporte_calculado:,.2f}"


# -----------------------------
# Otros gastos
# -----------------------------
st.number_input("Otros gastos ($)", min_value=0.0, step=1.0, key="otros")


# -----------------------------
# Cálculo
# -----------------------------
# Habitaciones necesarias (redondeo hacia arriba)
habitaciones = math.ceil(st.session_state["personas"] / st.session_state["por_habitacion"])

hospedaje_total = st.session_state["dias"] * st.session_state["hospedaje"] * habitaciones
alimentacion_total = st.session_state["dias"] * st.session_state["alimentacion"] * st.session_state["personas"]
transporte_total = transporte_calculado
otros_total = st.session_state["otros"]

total_viaticos = hospedaje_total + alimentacion_total + transporte_total + otros_total

if st.button("Calcular viáticos"):
    st.success(f"Total de viáticos: ${total_viaticos:,.2f}")

    # Detalle
    with st.expander("Ver desglose"):
        st.write(f"- Habitaciones: **{habitaciones}**")
        st.write(f"- Hospedaje total: **${hospedaje_total:,.2f}**")
        st.write(f"- Alimentación total: **${alimentacion_total:,.2f}**")
        st.write(f"- Transporte: **${transporte_total:,.2f}**  ({detalle_transporte})")
        st.write(f"- Otros: **${otros_total:,.2f}**")

    # Excel
    data = {
        "Días de viaje": [st.session_state["dias"]],
        "Personas": [st.session_state["personas"]],
        "Por habitación": [st.session_state["por_habitacion"]],
        "Habitaciones": [habitaciones],
        "Hospedaje por día": [st.session_state["hospedaje"]],
        "Hospedaje total": [hospedaje_total],
        "Alimentación por día": [st.session_state["alimentacion"]],
        "Alimentación total": [alimentacion_total],
        "Medio": [st.session_state["medio"]],
        "Detalle transporte": [detalle_transporte],
        "Transporte total": [transporte_total],
        "Otros": [otros_total],
        "TOTAL VIÁTICOS": [total_viaticos],
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        ws = writer.book.get_worksheet_by_name("Viaticos")

        # Autoajuste columnas: ancho basado en el valor más largo de cada columna
        for col_idx, col_name in enumerate(df.columns):
            max_len = max(
                [len(col_name)]
                + [len(str(v)) for v in df[col_name].astype(str).tolist()]
            )
            ws.set_column(col_idx, col_idx, min(max_len + 2, 50))

    st.download_button(
        "🗎 Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# -----------------------------
# Reset
# -----------------------------
if st.button("Reiniciar formulario"):
    reset_form()
