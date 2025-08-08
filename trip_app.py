import pandas as pd
from io import BytesIO
import streamlit as st
from PIL import Image

# Reinicio seguro al inicio del script
if st.session_state.get("reset", False):
    st.session_state["reset"] = False
    st.session_state["dias"] = 1
    st.session_state["hospedaje"] = 0.0
    st.session_state["alimentacion"] = 0.0
    st.session_state["transporte"] = 0.0
    st.session_state["personas"] = 1
    st.rerun()

# Cargar logo
logo = Image.open("logo.png")
st.image(logo, width=200)

# Título
st.title("💼 Calculadora de Viáticos")

# Inicializar estado si no existe
if "dias" not in st.session_state:
    st.session_state["dias"] = 1
if "hospedaje" not in st.session_state:
    st.session_state["hospedaje"] = 0.0
if "alimentacion" not in st.session_state:
    st.session_state["alimentacion"] = 0.0
if "transporte" not in st.session_state:
    st.session_state["transporte"] = 0.0
if "personas" not in st.session_state:
    st.session_state["personas"] = 1

# Inputs
st.number_input("Días de viaje", min_value=1, key="dias")
st.number_input("Hospedaje por día ($)", min_value=0.0, key="hospedaje")
st.number_input("Alimentación por día ($)", min_value=0.0, key="alimentacion")
st.number_input("Transporte total ($)", min_value=0.0, key="transporte")
st.number_input("Número de personas", min_value=1, key="personas")

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

# Botón de reset (marca bandera, reset se hace al inicio)
if st.button("Reiniciar formulario"):
    st.session_state["reset"] = True
    st.rerun()
