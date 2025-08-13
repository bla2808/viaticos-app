import pandas as pd
from io import BytesIO
import streamlit as st
from PIL import Image

# Reinicio seguro al inicio del script
if st.session_state.get("reset", False):
    st.session_state.clear()
    st.session_state["reset"] = False
    st.rerun()

# Cargar logo
logo = Image.open("logo.png")
st.image(logo, width=200)

# Título
st.title("💼 Calculadora de Viáticos")

# Inicializar estado si no existe
defaults = {
    "dias": 1,
    "hospedaje": 0.0,
    "alimentacion": 0.0,
    "transporte": 0.0,
    "personas": 1,
    "medio": "Auto",
    "boleto": 0.0,   # total boletos
    "otros": 0.0,
    "km_litro": 0.0,
    "precio_gasolina": 0.0,
    "distancia_km": 0.0,
    "casetas": 0.0
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Entradas
st.number_input("Días de viaje", min_value=1, key="dias")
st.number_input("Hospedaje por día ($)", min_value=0.0, key="hospedaje")
st.number_input("Alimentación por día ($)", min_value=0.0, key="alimentacion")
st.number_input("Transporte total ($)", min_value=0.0, key="transporte")
st.number_input("Número de personas", min_value=1, key="personas")

st.selectbox("Medio de transporte", ["Auto", "Avión", "Otro"], key="medio")

if st.session_state["medio"] == "Avión":
    st.number_input("Boleto de avión (total) ($)", min_value=0.0, key="boleto")
    st.session_state["km_litro"] = 0.0
    st.session_state["precio_gasolina"] = 0.0
    st.session_state["distancia_km"] = 0.0
    st.session_state["casetas"] = 0.0

elif st.session_state["medio"] == "Auto":
    st.number_input("Km por litro", min_value=0.0, key="km_litro")
    st.number_input("Precio gasolina ($/litro)", min_value=0.0, key="precio_gasolina")
    st.number_input("Distancia total (km)", min_value=0.0, key="distancia_km")
    st.number_input("Costo total casetas ($)", min_value=0.0, key="casetas")
    st.session_state["boleto"] = 0.0

else:
    st.session_state["boleto"] = 0.0
    st.session_state["km_litro"] = 0.0
    st.session_state["precio_gasolina"] = 0.0
    st.session_state["distancia_km"] = 0.0
    st.session_state["casetas"] = 0.0

st.number_input("Otros gastos ($)", min_value=0.0, key="otros")

# --- Cálculo
if st.button("Calcular viáticos"):
    base = st.session_state["dias"] * (st.session_state["hospedaje"] + st.session_state["alimentacion"]) * st.session_state["personas"]
    
    # Cálculo gasolina si es auto
    if st.session_state["medio"] == "Auto" and st.session_state["km_litro"] > 0:
        gasolina_total = (st.session_state["distancia_km"] / st.session_state["km_litro"]) * st.session_state["precio_gasolina"]
    else:
        gasolina_total = 0.0
    
    total = base + st.session_state["transporte"] + st.session_state["boleto"] + st.session_state["otros"] + gasolina_total + st.session_state["casetas"]

    st.success(f"Total de viáticos: ${total:,.2f}")

    # DataFrame detallado
    df = pd.DataFrame([{
        "Días de viaje": st.session_state["dias"],
        "Personas": st.session_state["personas"],
        "Medio de transporte": st.session_state["medio"],
        "Hospedaje por día": st.session_state["hospedaje"],
        "Alimentación por día": st.session_state["alimentacion"],
        "Transporte total": st.session_state["transporte"],
        "Boleto avión (total)": st.session_state["boleto"],
        "Km por litro": st.session_state["km_litro"],
        "Precio gasolina": st.session_state["precio_gasolina"],
        "Distancia km": st.session_state["distancia_km"],
        "Gasolina total": gasolina_total,
        "Casetas": st.session_state["casetas"],
        "Otros": st.session_state["otros"],
        "Total Viáticos": total
    }])

    # Guardar en Excel con autoajuste de columnas y formatos
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

        cols_moneda = ["Hospedaje por día", "Alimentación por día", "Transporte total", "Boleto avión (total)", "Precio gasolina", "Gasolina total", "Casetas", "Otros", "Total Viáticos"]
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

# Botón de reset
if st.button("Reiniciar formulario"):
    st.session_state["reset"] = True
    st.rerun()
