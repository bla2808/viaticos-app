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

if st.button("Calcular viáticos"):
    total = (dias * (hospedaje + alimentacion) + transporte) * personas
    st.success(f"Total de viáticos: ${total:,.2f}")
