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


def download_gingipains(tsv_path="gingipains.tsv"):
    query = {
        "query": UNIPROT_QUERY,
        "format": "tsv",
        "fields": ",".join(FIELDS),
        "size": "100",
    }
    url = UNIPROT_URL + "?" + urllib.parse.urlencode(query)
    print(f"Descargando datos de UniProt:\n{url}\n")
    with urllib.request.urlopen(url) as response:
        raw = response.read().decode("utf-8")
    if not raw.strip():
        raise RuntimeError("No se recibieron datos de UniProt.")
    with open(tsv_path, "w", encoding="utf-8", newline="") as out_file:
        out_file.write(raw)
    print(f"Guardado el archivo {tsv_path}")
    return tsv_path


def load_to_sqlite(tsv_path="gingipains.tsv", db_path="moleculas.db"):
    print(f"Importando {tsv_path} a {db_path}")
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
            sequence TEXT,
            function TEXT
        )
        """
    )
    with open(tsv_path, encoding="utf-8", newline="") as in_file:
        reader = csv.DictReader(in_file, delimiter="\t")
        rows = []
        for row in reader:
            organism = (row.get("Organism") or row.get("organism_name") or "").strip()
            if "Porphyromonas gingivalis" not in organism:
                continue
            rows.append(
                (
                    row.get("Entry") or row.get("accession"),
                    row.get("Entry name") or row.get("id"),
                    row.get("Protein names") or row.get("protein_name"),
                    organism,
                    row.get("Gene names") or row.get("gene_names"),
                    row.get("Sequence") or row.get("sequence"),
                    "",
                )
            )
    cur.executemany(
        """
        INSERT OR REPLACE INTO gingipains
        (accession, uniprot_id, protein_name, organism_name, gene_names, sequence, function)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    print(f"Importación terminada: {len(rows)} filas cargadas.")
    return db_path


def main():
    tsv_path = "gingipains.tsv"
    db_path = "moleculas.db"
    if "--no-db" in sys.argv:
        download_gingipains(tsv_path)
        return
    download_gingipains(tsv_path)
    load_to_sqlite(tsv_path, db_path)
    print("\nEjemplo de consulta:")
    print('  sqlite3 moleculas.db "SELECT accession, protein_name, organism_name FROM gingipains LIMIT 10;"')


if __name__ == "__main__":
    main()
