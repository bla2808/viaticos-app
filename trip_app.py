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
defaults = {
    "dias": 1,
    "hospedaje": 0.0,
    "alimentacion": 0.0,
    "transporte": 0.0,
    "personas": 1,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Inputs
st.number_input("Días de viaje", min_value=1, key="dias")
st.number_input("Hospedaje por día ($)", min_value=0.0, key="hospedaje")
st.number_input("Alimentación por día ($)", min_value=0.0, key="alimentacion")
st.number_input("Transporte total ($)", min_value=0.0, key="transporte")
st.number_input("Número de personas", min_value=1, key="personas")

# Botón de cálculo
if st.button("Calcular viáticos"):
    total = (
        st.session_state["dias"]
        * (st.session_state["hospedaje"] + st.session_state["alimentacion"])
        + st.session_state["transporte"]
    ) * st.session_state["personas"]

    st.success(f"Total de viáticos: ${total:,.2f}")

    # Crear DataFrame
    df = pd.DataFrame([{
        "Días de viaje": st.session_state["dias"],
        "Hospedaje por día": st.session_state["hospedaje"],
        "Alimentación por día": st.session_state["alimentacion"],
        "Transporte total": st.session_state["transporte"],
        "Personas": st.session_state["personas"],
        "Total Viáticos": total
    }])

    # Guardar en Excel con autoajuste de columnas y formatos
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Viaticos")
        workbook  = writer.book
        worksheet = writer.sheets["Viaticos"]

        # Formatos
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
        money_fmt  = workbook.add_format({"num_format": "$#,##0.00"})

        # Encabezados con formato
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_fmt)

        # Autoajuste de columnas (máximo entre header y valores + padding)
        for col_num, col_name in enumerate(df.columns):
            series_as_str = df[col_name].astype(str)
            max_len_vals = series_as_str.map(len).max() if len(series_as_str) else 0
            max_len = max(max_len_vals, len(col_name)) + 2  # padding
            worksheet.set_column(col_num, col_num, max_len)

        # Formato moneda a columnas relevantes
        cols_moneda = ["Hospedaje por día", "Alimentación por día", "Transporte total", "Total Viáticos"]
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

# Botón de reset (marca bandera; el reset se aplica al inicio)
if st.button("Reiniciar formulario"):
    st.session_state["reset"] = True
    st.rerun()
