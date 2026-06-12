import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dashboard Paid Media Internacional",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard Paid Media Internacional")
st.caption("Evolución mensual por país + consolidado Regional")

REQUIRED_COLUMNS = [
    "Fecha", "País", "Importe Gastado", "Alcance",
    "Impresiones", "Clics", "Leads", "Ventas"
]

METRICAS_VOLUMEN = [
    "Importe Gastado", "Alcance", "Impresiones", "Clics", "Leads", "Ventas"
]

def normalize_col(col):
    return str(col).strip()

def clean_number(value):
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float, np.number)):
        return value
    value = str(value)
    value = re.sub(r"[^0-9,.\-]", "", value)

    # Manejo de formatos tipo 1.234,56 o 1,234.56
    if value.count(",") == 1 and value.count(".") >= 1 and value.rfind(",") > value.rfind("."):
        value = value.replace(".", "").replace(",", ".")
    elif value.count(",") > 0 and value.count(".") == 0:
        value = value.replace(",", ".")
    else:
        value = value.replace(",", "")

    try:
        return float(value)
    except Exception:
        return 0

@st.cache_data(show_spinner=False)
def load_from_csv_url(url):
    return pd.read_csv(url)

@st.cache_data(show_spinner=False)
def load_from_excel(file):
    return pd.read_excel(file)

def prepare_data(df):
    df = df.copy()
    df.columns = [normalize_col(c) for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas obligatorias: {', '.join(missing)}")
        st.stop()

    df = df[REQUIRED_COLUMNS].copy()

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["País"] = df["País"].astype(str).str.strip()

    for col in METRICAS_VOLUMEN:
        df[col] = df[col].apply(clean_number)

    df = df.dropna(subset=["Fecha"])
    df = df[df["País"].notna() & (df["País"] != "")]
    df["Mes"] = df["Fecha"].dt.to_period("M").dt.to_timestamp()

    return df

def aggregate_data(df, dims):
    agg = (
        df.groupby(dims, dropna=False)[METRICAS_VOLUMEN]
        .sum()
        .reset_index()
    )

    agg["CTR"] = np.where(
        agg["Impresiones"] > 0,
        agg["Clics"] / agg["Impresiones"],
        0
    )
    agg["CPL"] = np.where(
        agg["Leads"] > 0,
        agg["Importe Gastado"] / agg["Leads"],
        0
    )
    agg["CPA"] = np.where(
        agg["Ventas"] > 0,
        agg["Importe Gastado"] / agg["Ventas"],
        0
    )

    return agg

def format_money(x):
    return f"${x:,.0f}"

def format_percent(x):
    return f"{x:.2%}"

with st.sidebar:
    st.header("Fuente de datos")

    default_url = st.secrets.get("GOOGLE_SHEET_CSV_URL", "") if hasattr(st, "secrets") else ""

    google_sheet_url = st.text_input(
        "URL CSV/export de Google Sheets",
        value=default_url,
        placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=0"
    )

    uploaded_file = st.file_uploader(
        "O carga un Excel manualmente",
        type=["xlsx", "xls", "csv"]
    )

    st.divider()
    st.caption("La hoja debe tener columnas: Fecha, País, Importe Gastado, Alcance, Impresiones, Clics, Leads, Ventas.")

if uploaded_file is not None:
    if uploaded_file.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = load_from_excel(uploaded_file)
elif google_sheet_url:
    raw_df = load_from_csv_url(google_sheet_url)
else:
    st.info("Ingresa una URL CSV/export de Google Sheets o carga un archivo Excel/CSV.")
    st.stop()

df = prepare_data(raw_df)

with st.sidebar:
    st.header("Filtros")

    paises = sorted(df["País"].dropna().unique())
    paises_sel = st.multiselect(
        "País",
        options=paises,
        default=paises
    )

    min_date = df["Mes"].min().date()
    max_date = df["Mes"].max().date()

    date_range = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    objetivo_cpa = st.number_input("Objetivo CPA", min_value=0.0, value=50.0, step=1.0)
    objetivo_cpl = st.number_input("Objetivo CPL", min_value=0.0, value=10.0, step=1.0)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    (df["País"].isin(paises_sel)) &
    (df["Mes"].dt.date >= start_date) &
    (df["Mes"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

regional = aggregate_data(filtered, ["Mes"])
pais_mes = aggregate_data(filtered, ["Mes", "País"])
pais_total = aggregate_data(filtered, ["País"])

regional_total = aggregate_data(filtered.assign(Regional="Regional"), ["Regional"]).iloc[0]

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

kpi1.metric("Importe Gastado", format_money(regional_total["Importe Gastado"]))
kpi2.metric("Alcance", f"{regional_total['Alcance']:,.0f}")
kpi3.metric("Impresiones", f"{regional_total['Impresiones']:,.0f}")
kpi4.metric("Clics", f"{regional_total['Clics']:,.0f}")
kpi5.metric("Leads", f"{regional_total['Leads']:,.0f}")
kpi6.metric("Ventas", f"{regional_total['Ventas']:,.0f}")

kpi7, kpi8, kpi9 = st.columns(3)
kpi7.metric("CTR Regional", format_percent(regional_total["CTR"]))
kpi8.metric("CPL Regional", format_money(regional_total["CPL"]))
kpi9.metric("CPA Regional", format_money(regional_total["CPA"]))

st.divider()

st.subheader("Evolución mensual por país")

metricas_izquierda = st.multiselect(
    "Métricas eje izquierdo",
    options=["Importe Gastado", "Alcance", "Impresiones"],
    default=["Importe Gastado", "Alcance"]
)

metricas_derecha = st.multiselect(
    "Métricas eje derecho",
    options=["Clics", "Leads", "Ventas"],
    default=["Clics", "Leads", "Ventas"]
)

fig = go.Figure()

for pais in pais_mes["País"].unique():
    temp = pais_mes[pais_mes["País"] == pais].sort_values("Mes")

    for metrica in metricas_izquierda:
        fig.add_trace(
            go.Scatter(
                x=temp["Mes"],
                y=temp[metrica],
                mode="lines+markers",
                name=f"{pais} - {metrica}",
                yaxis="y1"
            )
        )

    for metrica in metricas_derecha:
        fig.add_trace(
            go.Scatter(
                x=temp["Mes"],
                y=temp[metrica],
                mode="lines+markers",
                name=f"{pais} - {metrica}",
                yaxis="y2"
            )
        )

fig.update_layout(
    height=620,
    hovermode="x unified",
    xaxis_title="Mes",
    yaxis=dict(title="Gasto / Alcance / Impresiones"),
    yaxis2=dict(
        title="Clics / Leads / Ventas",
        overlaying="y",
        side="right"
    ),
    legend=dict(orientation="h", y=-0.25)
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Consolidado Regional mensual")

regional_display = regional.copy()
regional_display["CTR"] = regional_display["CTR"].map(lambda x: f"{x:.2%}")
regional_display["CPL"] = regional_display["CPL"].map(lambda x: f"${x:,.2f}")
regional_display["CPA"] = regional_display["CPA"].map(lambda x: f"${x:,.2f}")
regional_display["Mes"] = regional_display["Mes"].dt.strftime("%Y-%m")

st.dataframe(regional_display, use_container_width=True, hide_index=True)

st.subheader("Tabla de eficiencia por mes y país")

eff = pais_mes.copy()
eff["Mes"] = eff["Mes"].dt.strftime("%Y-%m")

def style_efficiency(data):
    styled = data.style
    if "CPA" in data.columns:
        styled = styled.map(
            lambda v: "background-color: #ffcccc;" if isinstance(v, (int, float)) and v > objetivo_cpa else "",
            subset=["CPA"]
        )
    if "CPL" in data.columns:
        styled = styled.map(
            lambda v: "background-color: #ccffcc;" if isinstance(v, (int, float)) and v <= objetivo_cpl else "",
            subset=["CPL"]
        )
    return styled.format({
        "Importe Gastado": "${:,.2f}",
        "Alcance": "{:,.0f}",
        "Impresiones": "{:,.0f}",
        "Clics": "{:,.0f}",
        "Leads": "{:,.0f}",
        "Ventas": "{:,.0f}",
        "CTR": "{:.2%}",
        "CPL": "${:,.2f}",
        "CPA": "${:,.2f}",
    })

st.dataframe(style_efficiency(eff), use_container_width=True, hide_index=True)

st.subheader("Ranking por país")

ranking = pais_total.sort_values("Importe Gastado", ascending=False).copy()

fig_rank = go.Figure()
fig_rank.add_trace(go.Bar(
    x=ranking["País"],
    y=ranking["Importe Gastado"],
    name="Importe Gastado"
))
fig_rank.update_layout(
    height=420,
    xaxis_title="País",
    yaxis_title="Importe Gastado"
)

st.plotly_chart(fig_rank, use_container_width=True)

with st.expander("Ver datos normalizados"):
    st.dataframe(df, use_container_width=True, hide_index=True)