# Dashboard Paid Media en Streamlit

## Archivos
- `app.py`: aplicación principal.
- `requirements.txt`: dependencias para Streamlit Cloud.

## Cómo conectar Google Sheets

La hoja debe tener estas columnas:

`Fecha`, `País`, `Importe Gastado`, `Alcance`, `Impresiones`, `Clics`, `Leads`, `Ventas`

### Opción simple
Publica la pestaña de Google Sheets como CSV y usa una URL con este formato:

`https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=GID_DE_LA_HOJA`

En Streamlit puedes pegar esa URL en el sidebar.

### Opción con secrets
En Streamlit Cloud, agrega este secret:

```toml
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=GID_DE_LA_HOJA"
```

## Deploy
1. Sube estos archivos a GitHub.
2. Entra a Streamlit Cloud.
3. Crea una app nueva desde el repositorio.
4. Selecciona `app.py`.
5. Agrega el secret si quieres dejar la URL fija.