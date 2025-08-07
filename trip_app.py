import pandas as pd
from io import BytesIO

import streamlit as st

from PIL import Image 

logo = Image.open("logo.png")
st.image(logo, width=200)

st.title("💼 Calculadora de Viáticos")

dias = st.number_input("Días de viaje", min_value=1, step=1)
hospedaje = st.number_input("Hospedaje por día ($)", min_value=0.0, step=10.0)
alimentacion = st.number_input("Alimentación por día ($)", min_value=0.0, step=10.0)
transporte = st.number_input("Transporte total ($)", min_value=0.0, step=10.0)
personas = st.number_input("Número de personas", min_value=1, step=1)
datos = {
    "Días de viaje": dias,
    "Hospedaje por día ($)": hospedaje,
    "Alimentación por día ($)": alimentacion,
    "Transporte total ($)": transporte,
    "Número de personas": personas
}

if st.button("Calcular viáticos"):
    total = (dias * (hospedaje + alimentacion) + transporte) * personas
    st.success(f"Total de viáticos: ${total:,.2f}")


# Crear DataFrame y añadir el total
    df = pd.DataFrame([datos])
    df["Total de viáticos ($)"] = total

    # Convertir a Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Viáticos')

    st.download_button(
        label="📥 Descargar Excel",
        data=output.getvalue(),
        file_name="viaticos_SEPAC.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
