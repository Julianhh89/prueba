#!/usr/bin/env python3
"""Descarga datos de gingipain de UniProt y los guarda en un TSV.
También puede crear una base de datos SQLite llamada moleculas.db.
"""

from __future__ import annotations
import csv
import sqlite3
import sys
import urllib.parse
import urllib.request

UNIPROT_QUERY = '(gene:rgpA OR gene:rgpB OR gene:kgp OR protein_name:gingipain)'
FIELDS = [
    "accession",
    "id",
    "protein_name",
    "organism_name",
    "gene_names",
    "sequence",
]
UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/search"
CSV_PATH = "gingipains.csv"


def download_gingipains(tsv_path="gingipains.tsv"):
    """Descarga TODOS los resultados de UniProt con paginación."""
    query = {
        "query": UNIPROT_QUERY,
        "format": "tsv",
        "fields": ",".join(FIELDS),
        "size": "500",
    }
    url = UNIPROT_URL + "?" + urllib.parse.urlencode(query)
    print(f"Descargando datos de UniProt (con paginación):\n{url}\n")
    
    all_data = []
    cursor = None
    page = 1
    
    while True:
        current_query = query.copy()
        if cursor:
            current_query["cursor"] = cursor
        
        current_url = UNIPROT_URL + "?" + urllib.parse.urlencode(current_query)
        print(f"  Página {page}...", end=" ", flush=True)
        
        with urllib.request.urlopen(current_url) as response:
            raw = response.read().decode("utf-8")
            headers = response.headers
        
        if not raw.strip():
            print("vacía")
            break
        
        lines = raw.strip().split("\n")
        if page == 1 and lines:
            all_data.append(lines[0])
        
        if len(lines) > 1:
            all_data.extend(lines[1:])
        
        total = headers.get("X-Total-Results")
        if total:
            print(f"({len(lines)-1} registros, total: {total})")
        else:
            print(f"({len(lines)-1} registros)")
        
        link_header = headers.get("Link", "")
        cursor = None
        if "rel=\"next\"" in link_header:
            for link in link_header.split(","):
                if "rel=\"next\"" in link:
                    import re
                    match = re.search(r'cursor=([^&;>\s]+)', link)
                    if match:
                        cursor = match.group(1)
                    break
        
        if not cursor:
            break
        
        page += 1
    
    if not all_data:
        raise RuntimeError("No se recibieron datos de UniProt.")
    
    with open(tsv_path, "w", encoding="utf-8", newline="") as out_file:
        out_file.write("\n".join(all_data))
        if all_data[-1]:
            out_file.write("\n")
    print(f"Guardado el archivo {tsv_path}")
    return tsv_path


def load_to_sqlite(tsv_path="gingipains.tsv", db_path="moleculas.db", filter_organism=None):
    """Importa datos a SQLite. Si filter_organism=None, importa todos.
    Si filter_organism="Porphyromonas gingivalis", filtra a esa especie."""
    
    label = f" ({filter_organism})" if filter_organism else " (todos los organismos)"
    print(f"Importando{label} a {db_path}")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gingipains (
            accession TEXT PRIMARY KEY,
            uniprot_id TEXT,
            protein_name TEXT,
            organism_name TEXT,
            gene_names TEXT,
            sequence TEXT
        )
        """
    )
    
    with open(tsv_path, encoding="utf-8", newline="") as in_file:
        reader = csv.DictReader(in_file, delimiter="\t")
        rows = []
        for row in reader:
            organism = (row.get("Organism") or row.get("organism_name") or "").strip()
            
            if filter_organism and filter_organism not in organism:
                continue
            
            rows.append(
                (
                    row.get("Entry") or row.get("accession"),
                    row.get("Entry name") or row.get("id"),
                    row.get("Protein names") or row.get("protein_name"),
                    organism,
                    row.get("Gene names") or row.get("gene_names"),
                    row.get("Sequence") or row.get("sequence"),
                )
            )
    
    cur.executemany(
        """
        INSERT OR REPLACE INTO gingipains
        (accession, uniprot_id, protein_name, organism_name, gene_names, sequence)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    
    conn.commit()
    conn.close()
    print(f"Importación terminada: {len(rows)} filas cargadas en {db_path}")
    return db_path


def tsv_to_csv(tsv_path="gingipains.tsv", csv_path="gingipains.csv", filter_organism=None):
    """Convierte TSV a CSV. Si filter_organism=None, exporta todos."""
    label = f" ({filter_organism})" if filter_organism else " (todos)"
    print(f"Convirtiendo TSV a CSV{label}: {csv_path}")
    
    with open(tsv_path, encoding="utf-8", newline="") as in_file:
        reader = csv.DictReader(in_file, delimiter="\t")
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise RuntimeError("No se pudieron leer los encabezados del TSV.")
        
        rows = []
        for row in reader:
            if filter_organism:
                organism = (row.get("Organism") or row.get("organism_name") or "").strip()
                if filter_organism not in organism:
                    continue
            rows.append(row)
        
        with open(csv_path, "w", encoding="utf-8", newline="") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    
    print(f"Guardado: {csv_path} ({len(rows)} filas)")
    return csv_path


def main():
    tsv_path = "gingipains.tsv"
    
    if "--no-db" in sys.argv:
        download_gingipains(tsv_path)
        tsv_to_csv(tsv_path, "gingipains_todos.csv", filter_organism=None)
        tsv_to_csv(tsv_path, "gingipains_gingivalis.csv", filter_organism="Porphyromonas gingivalis")
        return
    
    download_gingipains(tsv_path)
    
    print("\n=== Generando versión COMPLETA (todos los organismos) ===")
    tsv_to_csv(tsv_path, "gingipains_todos.csv", filter_organism=None)
    load_to_sqlite(tsv_path, "moleculas_todos.db", filter_organism=None)
    
    print("\n=== Generando versión FILTRADA (solo P. gingivalis) ===")
    tsv_to_csv(tsv_path, "gingipains_gingivalis.csv", filter_organism="Porphyromonas gingivalis")
    load_to_sqlite(tsv_path, "moleculas_gingivalis.db", filter_organism="Porphyromonas gingivalis")
    
    print("\n✓ Archivos generados:")
    print("  - gingipains_todos.csv (todas las proteínas)")
    print("  - gingipains_gingivalis.csv (solo P. gingivalis)")
    print("  - moleculas_todos.db (todas las proteínas)")
    print("  - moleculas_gingivalis.db (solo P. gingivalis)")


if __name__ == "__main__":
    main()
