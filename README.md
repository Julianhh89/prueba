# prueba
prueba_uso_github_1

## Descargar datos de gingipain

Este repositorio incluye un script para traer datos de gingipains de UniProt y crear una base de datos SQLite local.

Usa:

```bash
python3 fetch_gingipains.py
```

Esto genera:

- `gingipains.tsv` con los datos descargados
- `gingipains.csv` con los mismos datos en formato CSV
- `moleculas.db` con la tabla `gingipains`

Si solo quieres descargar el TSV y CSV sin crear la base de datos:

```bash
python3 fetch_gingipains.py --no-db
```
