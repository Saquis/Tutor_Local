"""Adaptador: caché en SQLite.

Implementa el puerto Cache. Repetir una lección cuesta cero.

Ubicación de la BD: por defecto en la carpeta del servidor, pero
se puede mover (en este proyecto lo pesado va en WSL).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from ..dominio.entidades import Leccion, Pregunta

ESQUEMA = """
CREATE TABLE IF NOT EXISTS cache (
    huella    TEXT PRIMARY KEY,
    url       TEXT NOT NULL,
    titulo    TEXT,
    resumen   TEXT,
    preguntas TEXT,
    creado    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_url ON cache(url);
"""


class CacheSqlite:
    """Implementa Cache. Guarda resumen y preguntas por separado
    (el resumen llega antes; las preguntas llegan después)."""

    def __init__(self, ruta: str | Path = "study.db") -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.ruta), check_same_thread=False)
        self._db.executescript(ESQUEMA)
        self._db.commit()

    # --- puerto ---

    def huella(self, leccion: Leccion) -> str:
        base = f"{leccion.url}\x00{leccion.contenido_efectivo[:20000]}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def obtener(self, huella: str) -> tuple[str | None, list[Pregunta] | None]:
        fila = self._db.execute(
            "SELECT resumen, preguntas FROM cache WHERE huella = ?", (huella,)
        ).fetchone()
        if not fila:
            return None, None
        resumen, preguntas_json = fila
        preguntas = None
        if preguntas_json:
            try:
                preguntas = [
                    Pregunta(
                        enunciado=p["enunciado"],
                        opciones=tuple(p["opciones"]),
                        respuesta=p["respuesta"],
                        porque=p.get("porque", ""),
                    )
                    for p in json.loads(preguntas_json)
                ]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                preguntas = None
        return (resumen or None), preguntas

    def guardar_resumen(self, huella: str, leccion: Leccion, resumen: str) -> None:
        self._upsert(huella, leccion, resumen=resumen)

    def guardar_preguntas(self, huella: str, preguntas: list[Pregunta]) -> None:
        payload = json.dumps(
            [
                {
                    "enunciado": p.enunciado,
                    "opciones": list(p.opciones),
                    "respuesta": p.respuesta,
                    "porque": p.porque,
                }
                for p in preguntas
            ],
            ensure_ascii=False,
        )
        self._upsert(huella, None, preguntas=payload)

    # --- interno ---

    def _upsert(self, huella: str, leccion: Leccion | None, **campos) -> None:
        fila = self._db.execute(
            "SELECT url, titulo, resumen, preguntas FROM cache WHERE huella = ?", (huella,)
        ).fetchone()

        if fila is None:
            self._db.execute(
                "INSERT INTO cache (huella, url, titulo, resumen, preguntas, creado) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    huella,
                    leccion.url if leccion else "",
                    leccion.titulo if leccion else "",
                    campos.get("resumen"),
                    campos.get("preguntas"),
                    time.time(),
                ),
            )
        else:
            url, titulo, resumen_prev, preguntas_prev = fila
            self._db.execute(
                "UPDATE cache SET url=?, titulo=?, resumen=?, preguntas=? WHERE huella=?",
                (
                    leccion.url if leccion else url,
                    leccion.titulo if leccion else titulo,
                    campos.get("resumen", resumen_prev),
                    campos.get("preguntas", preguntas_prev),
                    huella,
                ),
            )
        self._db.commit()

    def estadisticas(self) -> dict:
        total = self._db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        con_resumen = self._db.execute(
            "SELECT COUNT(*) FROM cache WHERE resumen IS NOT NULL AND resumen != ''"
        ).fetchone()[0]
        con_preguntas = self._db.execute(
            "SELECT COUNT(*) FROM cache WHERE preguntas IS NOT NULL AND preguntas != ''"
        ).fetchone()[0]
        return {"total": total, "con_resumen": con_resumen, "con_preguntas": con_preguntas}

    def cerrar(self) -> None:
        self._db.close()
