# Crediya | Dashboard Paid Media Internacional

Dashboard en Streamlit para visualizar evolución mensual de Paid Media por país y consolidado Regional.

## Funcionalidades

- Conexión a Google Sheets vía URL CSV/export.
- Carga manual de Excel o CSV.
- KPIs Regionales:
  - Importe Gastado
  - Alcance
  - Impresiones
  - Clics
  - Leads
  - Ventas
  - CTR
  - CPL
  - CPA
  - CVR Lead
  - CVR Venta
- Filtros por país y rango de fechas.
- Evolución mensual por país con ejes duales.
- Consolidado Regional mensual.
- Tabla de eficiencia con mapa de calor.
- Alertas tácticas cuando CPL o CPA superan objetivo.
- Exportación a Excel y CSV.

## Estructura requerida de Google Sheets

La pestaña conectada debe tener estas columnas:

```text
Fecha
País
Importe Gastado
Alcance
Impresiones
Clics
Leads
Ventas
```

Importante:

- No usar celdas combinadas.
- No incluir filas de totales al final.
- Los valores numéricos deben estar como números puros, sin símbolos de moneda.
- El formato de moneda debe aplicarse visualmente, no como texto dentro de la celda.
- `Fecha` debe representar el mes o una fecha dentro del mes.

## Cómo publicar Google Sheets como CSV

Usa una URL con este formato:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=GID
```

Donde:

- `SPREADSHEET_ID` es el ID del archivo de Google Sheets.
- `GID` es el ID de la pestaña específica.

## Deploy en Streamlit Cloud

1. Sube estos archivos al repositorio `camilovillate-tech/pauta`.
2. Entra a Streamlit Cloud.
3. Crea una nueva app.
4. Selecciona:
   - Repository: `camilovillate-tech/pauta`
   - Branch: `main`
   - Main file path: `app.py`
5. Haz clic en Deploy.

## Configurar la URL de Google Sheets como secret

En Streamlit Cloud, ve a:

```text
App > Settings > Secrets
```

Agrega:

```toml
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=GID"
```

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notas de modelado

Los campos calculados usan agregación correcta:

```text
CTR = SUM(Clics) / SUM(Impresiones)
CPL = SUM(Importe Gastado) / SUM(Leads)
CPA = SUM(Importe Gastado) / SUM(Ventas)
```

Esto evita errores por promediar porcentajes o ratios ya calculados.