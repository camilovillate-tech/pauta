import io
import re
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# Configuración general
# ============================================================

st.set_page_config(
    page_title="Crediya | Dashboard Paid Media",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND_PRIMARY = "#111827"
BRAND_ACCENT = "#2563EB"
BRAND_SUCCESS = "#16A34A"
BRAND_DANGER = "#DC2626"
BRAND_WARNING = "#F59E0B"

REQUIRED_COLUMNS = [
    "Fecha",
    "País",
    "Importe Gastado",
    "Alcance",
    "Impresiones",
    "Clics",
    "Leads",
    "Ventas",
]

VOLUME_METRICS = [
    "Importe Gastado",
    "Alcance",
    "Impresiones",
    "Clics",
    "Leads",
    "Ventas",
]

EFFICIENCY_METRICS = ["CTR", "CPL", "CPA", "CVR Lead", "CVR Venta"]

COUNTRY_ALIASES = {
    "panama": "Panamá",
    "panamá": "Panamá",
    "colombia": "Colombia",
    "mexico": "México",
    "méxico": "México",
    "peru": "Perú",
    "perú": "Perú",
    "regional": "Regional",
}


# ============================================================
# Estilos
# ============================================================

st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 14px 16px;
        border-radius: 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    div[data-testid="stMetricLabel"] {
        color: #6B7280;
    }
    .section-card {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        padding: 16px 18px;
        border-radius: 18px;
        margin-bottom: 12px;
    }
    .small-note {
        color: #6B7280;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Utilidades
# ============================================================

def normalize_column_name(value: str) -> str:
    return str(value).strip().replace("\n", " ")


def normalize_country(value: str) -> str:
    raw = str(value).strip()
    key = raw.lower()
    return COUNTRY_ALIASES.get(key, raw)


def clean_number(value):
    """
    Convierte monedas o números con separadores latinos/anglosajones a float.
    Ejemplos soportados:
    - "$1,234.56"
    - "1.234,56"
    - "1234"
    - "1 234"
    """
    if pd.isna(value):
        return 0.0

    if isinstance(value, (int, float, np.number)):
        return float(value)

    txt = str(value).strip()
    if txt == "":
        return 0.0

    txt = re.sub(r"[^0-9,\.\-]", "", txt)

    if txt.count(",") == 1 and txt.count(".") >= 1 and txt.rfind(",") > txt.rfind("."):
        txt = txt.replace(".", "").replace(",", ".")
    elif txt.count(",") > 0 and txt.count(".") == 0:
        txt = txt.replace(",", ".")
    else:
        txt = txt.replace(",", "")

    try:
        return float(txt)
    except Exception:
        return 0.0


def detect_date_column(df: pd.DataFrame) -> pd.Series:
    """
    Soporta una columna Fecha ya normalizada.
    Si Fecha viene como mes en texto, pandas intenta convertirla.
    """
    fecha = pd.to_datetime(df["Fecha"], errors="coerce", dayfirst=True)
    return fecha


def money(value):
    return f"${value:,.0f}"


def number(value):
    return f"{value:,.0f}"


def pct(value):
    return f"{value:.2%}"


def safe_div(numerator, denominator):
    return np.where(denominator > 0, numerator / denominator, 0)


@st.cache_data(show_spinner=False)
def load_csv_from_url(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


@st.cache_data(show_spinner=False)
def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    return pd.read_excel(uploaded_file)


def prepare_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
            + ". La base debe contener exactamente estas columnas: "
            + ", ".join(REQUIRED_COLUMNS)
        )
        st.stop()

    df = df[REQUIRED_COLUMNS].copy()
    df["Fecha"] = detect_date_column(df)
    df["País"] = df["País"].apply(normalize_country)

    for col in VOLUME_METRICS:
        df[col] = df[col].apply(clean_number)

    df = df.dropna(subset=["Fecha"])
    df = df[df["País"].astype(str).str.strip() != ""]
    df["Mes"] = df["Fecha"].dt.to_period("M").dt.to_timestamp()
    df["Mes Label"] = df["Mes"].dt.strftime("%Y-%m")

    return df


def aggregate(df: pd.DataFrame, dims: list[str]) -> pd.DataFrame:
    agg = df.groupby(dims, dropna=False)[VOLUME_METRICS].sum().reset_index()

    agg["CTR"] = safe_div(agg["Clics"], agg["Impresiones"])
    agg["CPL"] = safe_div(agg["Importe Gastado"], agg["Leads"])
    agg["CPA"] = safe_div(agg["Importe Gastado"], agg["Ventas"])
    agg["CVR Lead"] = safe_div(agg["Leads"], agg["Clics"])
    agg["CVR Venta"] = safe_div(agg["Ventas"], agg["Leads"])

    return agg


def add_mom(df: pd.DataFrame, metric: str, group_col: str | None = None) -> pd.DataFrame:
    result = df.copy().sort_values("Mes")

    if group_col:
        result[f"{metric} MoM"] = result.groupby(group_col)[metric].pct_change()
    else:
        result[f"{metric} MoM"] = result[metric].pct_change()

    return result


def style_efficiency_table(data: pd.DataFrame, target_cpl: float, target_cpa: float):
    formatter = {
        "Importe Gastado": "${:,.2f}",
        "Alcance": "{:,.0f}",
        "Impresiones": "{:,.0f}",
        "Clics": "{:,.0f}",
        "Leads": "{:,.0f}",
        "Ventas": "{:,.0f}",
        "CTR": "{:.2%}",
        "CVR Lead": "{:.2%}",
        "CVR Venta": "{:.2%}",
        "CPL": "${:,.2f}",
        "CPA": "${:,.2f}",
    }

    def color_cpl(v):
        if not isinstance(v, (int, float, np.number)):
            return ""
        return "background-color: #DCFCE7; color: #166534;" if v <= target_cpl else ""

    def color_cpa(v):
        if not isinstance(v, (int, float, np.number)):
            return ""
        return "background-color: #FEE2E2; color: #991B1B;" if v > target_cpa else ""

    return (
        data.style
        .map(color_cpl, subset=["CPL"])
        .map(color_cpa, subset=["CPA"])
        .format(formatter)
    )


def build_download_excel(df: pd.DataFrame, regional: pd.DataFrame, pais: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Raw Data Normalizada")
        regional.to_excel(writer, index=False, sheet_name="Regional Mensual")
        pais.to_excel(writer, index=False, sheet_name="Pais Mensual")

    return output.getvalue()


# ============================================================
# Header
# ============================================================

st.markdown(
    """
    <div class="section-card">
        <h1 style="margin-bottom: 0;">Crediya | Dashboard Paid Media Internacional</h1>
        <p class="small-note">
            Monitoreo táctico de gasto, alcance, clics, leads, ventas y eficiencia por país.
            Los indicadores CTR, CPL y CPA se calculan con agregación correcta:
            SUM(Clics)/SUM(Impresiones), SUM(Gasto)/SUM(Leads), SUM(Gasto)/SUM(Ventas).
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Sidebar: fuente y filtros
# ============================================================

with st.sidebar:
    st.header("1. Fuente de datos")

    default_url = ""
    try:
        default_url = st.secrets.get("GOOGLE_SHEET_CSV_URL", "")
    except Exception:
        default_url = ""

    google_sheet_url = st.text_input(
        "Google Sheets CSV/export URL",
        value=default_url,
        placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=0",
    )

    uploaded_file = st.file_uploader(
        "O carga archivo Excel/CSV",
        type=["xlsx", "xls", "csv"],
    )

    st.caption(
        "Columnas requeridas: Fecha, País, Importe Gastado, Alcance, "
        "Impresiones, Clics, Leads, Ventas."
    )

    st.divider()

    st.header("2. Objetivos")
    target_cpl = st.number_input("Objetivo CPL", min_value=0.0, value=10.0, step=1.0)
    target_cpa = st.number_input("Objetivo CPA", min_value=0.0, value=50.0, step=1.0)


# ============================================================
# Carga de datos
# ============================================================

if uploaded_file is not None:
    raw_df = load_uploaded_file(uploaded_file)
elif google_sheet_url:
    raw_df = load_csv_from_url(google_sheet_url)
else:
    st.info("Ingresa la URL CSV/export de Google Sheets o carga un Excel/CSV para iniciar.")
    st.stop()

df = prepare_data(raw_df)

with st.sidebar:
    st.header("3. Filtros")

    countries = sorted(df["País"].dropna().unique())
    selected_countries = st.multiselect(
        "País",
        options=countries,
        default=countries,
    )

    min_month = df["Mes"].min().date()
    max_month = df["Mes"].max().date()

    selected_dates = st.date_input(
        "Rango de fechas",
        value=(min_month, max_month),
        min_value=min_month,
        max_value=max_month,
    )

    selected_metric = st.selectbox(
        "Métrica principal para ranking",
        options=["Importe Gastado", "Leads", "Ventas", "CPA", "CPL", "CTR"],
        index=0,
    )

if len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_month, max_month

filtered = df[
    (df["País"].isin(selected_countries))
    & (df["Mes"].dt.date >= start_date)
    & (df["Mes"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()


# ============================================================
# Modelado
# ============================================================

regional_month = aggregate(filtered, ["Mes"])
country_month = aggregate(filtered, ["Mes", "País"])
country_total = aggregate(filtered, ["País"])

regional_total = aggregate(filtered.assign(Regional="Regional"), ["Regional"]).iloc[0]

regional_month = add_mom(regional_month, "Importe Gastado")
regional_month = add_mom(regional_month, "Leads")
regional_month = add_mom(regional_month, "Ventas")
regional_month = add_mom(regional_month, "CPA")

country_month = add_mom(country_month, "Importe Gastado", "País")
country_month = add_mom(country_month, "Leads", "País")
country_month = add_mom(country_month, "Ventas", "País")
country_month = add_mom(country_month, "CPA", "País")


# ============================================================
# KPIs principales
# ============================================================

st.subheader("Resumen Regional")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Importe Gastado", money(regional_total["Importe Gastado"]))
k2.metric("Alcance", number(regional_total["Alcance"]))
k3.metric("Impresiones", number(regional_total["Impresiones"]))
k4.metric("Clics", number(regional_total["Clics"]))
k5.metric("Leads", number(regional_total["Leads"]))
k6.metric("Ventas", number(regional_total["Ventas"]))

e1, e2, e3, e4, e5 = st.columns(5)
e1.metric("CTR", pct(regional_total["CTR"]))
e2.metric("CPL", money(regional_total["CPL"]))
e3.metric("CPA", money(regional_total["CPA"]))
e4.metric("CVR Lead", pct(regional_total["CVR Lead"]))
e5.metric("CVR Venta", pct(regional_total["CVR Venta"]))

st.divider()


# ============================================================
# Evolución mensual
# ============================================================

left, right = st.columns([2, 1])

with left:
    st.subheader("Evolución mensual por país")

    left_axis = st.multiselect(
        "Eje izquierdo",
        options=["Importe Gastado", "Alcance", "Impresiones"],
        default=["Importe Gastado", "Alcance"],
    )

    right_axis = st.multiselect(
        "Eje derecho",
        options=["Clics", "Leads", "Ventas"],
        default=["Clics", "Leads", "Ventas"],
    )

    fig = go.Figure()

    for country in country_month["País"].unique():
        temp = country_month[country_month["País"] == country].sort_values("Mes")

        for metric in left_axis:
            fig.add_trace(
                go.Scatter(
                    x=temp["Mes"],
                    y=temp[metric],
                    mode="lines+markers",
                    name=f"{country} | {metric}",
                    yaxis="y1",
                )
            )

        for metric in right_axis:
            fig.add_trace(
                go.Scatter(
                    x=temp["Mes"],
                    y=temp[metric],
                    mode="lines+markers",
                    name=f"{country} | {metric}",
                    yaxis="y2",
                )
            )

    fig.update_layout(
        height=620,
        hovermode="x unified",
        xaxis_title="Mes",
        yaxis=dict(title="Gasto / Alcance / Impresiones"),
        yaxis2=dict(title="Clics / Leads / Ventas", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=20, r=20, t=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Mix por país")

    fig_pie = px.pie(
        country_total,
        names="País",
        values="Importe Gastado",
        hole=0.45,
        title="Distribución de gasto",
    )
    fig_pie.update_layout(height=330, margin=dict(l=20, r=20, t=45, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

    fig_bar = px.bar(
        country_total.sort_values(selected_metric, ascending=False),
        x="País",
        y=selected_metric,
        title=f"Ranking por {selected_metric}",
    )
    fig_bar.update_layout(height=330, margin=dict(l=20, r=20, t=45, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)


# ============================================================
# Eficiencia y alertas
# ============================================================

st.subheader("Eficiencia mensual por país")

eff_cols = [
    "Mes",
    "País",
    "Importe Gastado",
    "Impresiones",
    "Clics",
    "Leads",
    "Ventas",
    "CTR",
    "CPL",
    "CPA",
    "CVR Lead",
    "CVR Venta",
    "CPA MoM",
]

eff_table = country_month[eff_cols].copy()
eff_table["Mes"] = eff_table["Mes"].dt.strftime("%Y-%m")

st.dataframe(
    style_efficiency_table(eff_table, target_cpl=target_cpl, target_cpa=target_cpa),
    use_container_width=True,
    hide_index=True,
)

alerts = country_total[
    (country_total["CPA"] > target_cpa) | (country_total["CPL"] > target_cpl)
].copy()

with st.expander("Alertas tácticas de optimización", expanded=True):
    if alerts.empty:
        st.success("No hay países por encima de los objetivos CPL/CPA definidos.")
    else:
        for _, row in alerts.sort_values("CPA", ascending=False).iterrows():
            reasons = []
            if row["CPA"] > target_cpa:
                reasons.append(f"CPA {money(row['CPA'])} > objetivo {money(target_cpa)}")
            if row["CPL"] > target_cpl:
                reasons.append(f"CPL {money(row['CPL'])} > objetivo {money(target_cpl)}")

            st.warning(
                f"{row['País']}: " + " | ".join(reasons)
                + ". Revisar presupuesto, segmentación, creatividades y calidad de conversión."
            )


# ============================================================
# Consolidado regional
# ============================================================

st.subheader("Consolidado Regional mensual")

regional_display = regional_month.copy()
regional_display["Mes"] = regional_display["Mes"].dt.strftime("%Y-%m")

regional_cols = [
    "Mes",
    "Importe Gastado",
    "Alcance",
    "Impresiones",
    "Clics",
    "Leads",
    "Ventas",
    "CTR",
    "CPL",
    "CPA",
    "CVR Lead",
    "CVR Venta",
    "Importe Gastado MoM",
    "Leads MoM",
    "Ventas MoM",
    "CPA MoM",
]

st.dataframe(
    regional_display[regional_cols].style.format(
        {
            "Importe Gastado": "${:,.2f}",
            "Alcance": "{:,.0f}",
            "Impresiones": "{:,.0f}",
            "Clics": "{:,.0f}",
            "Leads": "{:,.0f}",
            "Ventas": "{:,.0f}",
            "CTR": "{:.2%}",
            "CPL": "${:,.2f}",
            "CPA": "${:,.2f}",
            "CVR Lead": "{:.2%}",
            "CVR Venta": "{:.2%}",
            "Importe Gastado MoM": "{:.2%}",
            "Leads MoM": "{:.2%}",
            "Ventas MoM": "{:.2%}",
            "CPA MoM": "{:.2%}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# Exportables
# ============================================================

st.subheader("Exportables")

excel_bytes = build_download_excel(
    df=filtered,
    regional=regional_display,
    pais=country_month,
)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        label="Descargar Excel procesado",
        data=excel_bytes,
        file_name="paid_media_dashboard_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with c2:
    st.download_button(
        label="Descargar CSV normalizado",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="raw_data_normalizada.csv",
        mime="text/csv",
    )

with st.expander("Auditoría: datos normalizados"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)