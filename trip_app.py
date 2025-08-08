import pandas as pd
from io import BytesIO
import streamlit as st
from PIL import Image

# Cargar logo
logo = Image.open("logo.png")
st.image(logo, width=200)

# Título
st.title("💼 Calculadora de Viáticos")

# Inicializar estado si no existe
for key, default in {
    "dias": 1,
    "hospedaje": 0.0,
    "alimentacion": 0.0,
    "transporte": 0.0,
    "personas": 1
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Inputs controlados
st.session_state["dias"] = st.number_input("Días de viaje", min_value=1, key="dias")
st.session_state["hospedaje"] = st.number_input("Hospedaje por día ($)", min_value=0.0, key="hospedaje")
st.session_state["alimentacion"] = st.number_input("Alimentación por día ($)", min_value=0.0, key="alimentacion")
st.session_state["transporte"] = st.number_input("Transporte total ($)", min_value=0.0, key="transporte")
st.session_state["personas"] = st.number_input("Número de personas", min_value=1, key="personas")

# Botón de cálculo
if st.button("Calcular viáticos"):
    total = (st.session_state["dias"] * (st.session_state["hospedaje"] + st.session_state["alimentacion"]) + st.session_state["transporte"]) * st.session_state["personas"]
    st.success(f"Total de viáticos: ${total:,.2f}")

    # Crear DataFrame
    data = {
        "Días de viaje": [st.session_state["dias"]],
        "Hospedaje por día": [st.session_state["hospedaje"]],
        "Alimentación por día": [st.session_state["alimentacion"]],
        "Transporte total": [st.session_state["transporte"]],
        "Personas": [st.session_state["personas"]],
        "Total Viáticos": [total]
    }
    df = pd.DataFrame(data)

    # Guardar en Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
    st.download_button(
        label="🗎 Descargar resultado en Excel",
        data=output.getvalue(),
        file_name="viaticos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Botón de reset
if st.button("Reiniciar formulario"):
    for key, default in {
        "dias": 1,
        "hospedaje": 0.0,
        "alimentacion": 0.0,
        "transporte": 0.0,
        "personas": 1
    }.items():
        st.session_state[key] = default
    st.experimental_rerun()
