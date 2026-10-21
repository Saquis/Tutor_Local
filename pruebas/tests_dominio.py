"""Tests del dominio y los casos de uso — Tutor Local.

Lo importante de estos tests: NO necesitan red, ni base de datos, ni
Ollama, ni navegador. Eso es exactamente lo que compra la arquitectura
hexagonal: el núcleo se prueba con adaptadores falsos.

Ejecutar:
    python -m unittest discover -s pruebas -v
"""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

# Permite ejecutar desde la raíz del proyecto
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servidor.aplicacion.filtro_examenes import FiltroExamenes          # noqa: E402
from servidor.aplicacion.resumir_leccion import ResumirLeccion         # noqa: E402
from servidor.dominio.entidades import Leccion, Pregunta               # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
#  Adaptadores FALSOS — implementan los puertos, sin tocar nada real
# ─────────────────────────────────────────────────────────────────────────────

class CacheFalso:
    """Guarda en memoria. Demuestra que el dominio no depende de SQLite."""

    def __init__(self, resumen=None, preguntas=None):
        self.datos: dict[str, tuple] = {}
        self.guardados_resumen = 0
        self.guardados_preguntas = 0
        if resumen:
            self.datos["HUELLA"] = (resumen, preguntas)

    def huella(self, leccion):
        return "HUELLA"

    def obtener(self, huella):
        return self.datos.get(huella, (None, None))

    def guardar_resumen(self, huella, leccion, resumen):
        self.guardados_resumen += 1
        _, preg = self.datos.get(huella, (None, None))
        self.datos[huella] = (resumen, preg)

    def guardar_preguntas(self, huella, preguntas):
        self.guardados_preguntas += 1
        res, _ = self.datos.get(huella, (None, None))
        self.datos[huella] = (res, preguntas)


class MotorRapidoFalso:
    """Emite trozos fijos. Sin Ollama, sin GPU."""

    def __init__(self, trozos=None, falla=False):
        self.trozos = trozos or ["Primera linea. ", "Segunda linea."]
        self.falla = falla
        self.llamado = 0

    async def resumir(self, leccion):
        self.llamado += 1
        if self.falla:
            raise RuntimeError("motor caido")
        for t in self.trozos:
            yield t


class MotorProfundoFalso:
    def __init__(self, preguntas=None):
        self.preguntas = preguntas or []
        self.llamado = 0

    async def generar(self, leccion, cuantas=5):
        self.llamado += 1
        return self.preguntas


def recolectar(generador):
    async def _run():
        return [ev async for ev in generador]
    return asyncio.run(_run())


# ─────────────────────────────────────────────────────────────────────────────
#  Entidades
# ─────────────────────────────────────────────────────────────────────────────

class TestLeccion(unittest.TestCase):

    def test_seleccion_manda_sobre_contexto(self):
        le = Leccion(url="u", titulo="t", texto="contexto largo " * 50,
                     seleccion="solo esto")
        self.assertIn("[SELECCIÓN]", le.contenido_efectivo)
        self.assertIn("solo esto", le.contenido_efectivo)

    def test_sin_seleccion_devuelve_texto(self):
        le = Leccion(url="u", titulo="t", texto="x" * 300)
        self.assertEqual(le.contenido_efectivo, "x" * 300)

    def test_texto_insuficiente_no_es_util(self):
        self.assertFalse(Leccion(url="u", titulo="t", texto="corto").es_util())

    def test_texto_suficiente_es_util(self):
        self.assertTrue(Leccion(url="u", titulo="t", texto="x" * 300).es_util())


class TestPregunta(unittest.TestCase):

    def test_pregunta_valida(self):
        p = Pregunta(enunciado="¿?", opciones=("a", "b"), respuesta=1)
        self.assertEqual(p.respuesta, 1)

    def test_sin_opciones_falla(self):
        with self.assertRaises(ValueError):
            Pregunta(enunciado="¿?", opciones=(), respuesta=0)

    def test_respuesta_fuera_de_rango_falla(self):
        with self.assertRaises(ValueError):
            Pregunta(enunciado="¿?", opciones=("a", "b"), respuesta=5)


# ─────────────────────────────────────────────────────────────────────────────
#  Filtro de exámenes (la decisión ética)
# ─────────────────────────────────────────────────────────────────────────────

class TestFiltroExamenes(unittest.TestCase):

    def setUp(self):
        self.f = FiltroExamenes()

    def test_detecta_proctoring(self):
        le = Leccion(url="https://x.com/exam", titulo="Final",
                     texto="proctor activo " * 30)
        self.assertTrue(self.f.es_examen(le))

    def test_detecta_pearsonvue(self):
        le = Leccion(url="https://pearsonvue.com/x", titulo="Cert",
                     texto="x" * 300)
        self.assertTrue(self.f.es_examen(le))

    def test_no_bloquea_exam_prep(self):
        """'Exam Prep' es estudio legítimo — no debe bloquearse."""
        le = Leccion(url="https://cursos.com/exam-prep-sql",
                     titulo="Exam Prep: SQL", texto="contenido de estudio " * 30)
        self.assertFalse(self.f.es_examen(le))

    def test_no_bloquea_estudio_normal(self):
        le = Leccion(url="https://udemy.com/curso", titulo="Índices SQL",
                     texto="Un índice acelera las búsquedas " * 20)
        self.assertFalse(self.f.es_examen(le))


# ─────────────────────────────────────────────────────────────────────────────
#  Caso de uso — el corazón. Aquí se ve por qué el hexagonal vale la pena.
# ─────────────────────────────────────────────────────────────────────────────

class TestResumirLeccion(unittest.TestCase):

    def _caso(self, cache=None, rapido=None, profundo=None):
        return ResumirLeccion(
            cache=cache or CacheFalso(),
            motor_rapido=rapido or MotorRapidoFalso(),
            motor_profundo=profundo or MotorProfundoFalso(),
            filtro=FiltroExamenes(),
        )

    def test_bloquea_examenes_antes_de_cualquier_motor(self):
        rapid = MotorRapidoFalso()
        caso = self._caso(rapido=rapid)
        le = Leccion(url="https://x.com/proctor", titulo="Examen", texto="y" * 400)

        eventos = recolectar(caso.ejecutar(le))

        self.assertEqual(rapid.llamado, 0, "NO debe llamar al modelo en un examen")
        self.assertEqual(eventos[0].tipo, "error")
        self.assertIn("evaluación", eventos[0].datos["msg"])

    def test_texto_insuficiente_no_llama_al_motor(self):
        rapid = MotorRapidoFalso()
        caso = self._caso(rapido=rapid)
        eventos = recolectar(caso.ejecutar(Leccion(url="u", titulo="t", texto="corto")))

        self.assertEqual(rapid.llamado, 0)
        self.assertEqual(eventos[0].tipo, "error")

    def test_cache_hit_no_llama_al_motor(self):
        cache = CacheFalso(resumen="Ya estaba resumido.")
        rapid = MotorRapidoFalso()
        caso = self._caso(cache=cache, rapido=rapid)

        eventos = recolectar(caso.ejecutar(Leccion(url="u", titulo="t", texto="x" * 400)))

        self.assertEqual(rapid.llamado, 0, "caché debe evitar el modelo")
        self.assertEqual(eventos[0].tipo, "resumen")
        self.assertTrue(eventos[0].datos["desde_cache"])

    def test_cache_miss_hace_streaming_y_guarda(self):
        cache = CacheFalso()
        rapid = MotorRapidoFalso(trozos=["Uno. ", "Dos."])
        caso = self._caso(cache=cache, rapido=rapid)

        eventos = recolectar(caso.ejecutar(Leccion(url="u", titulo="t", texto="x" * 400)))

        tipos = [e.tipo for e in eventos]
        self.assertIn("status", tipos)
        self.assertEqual(tipos.count("token"), 2, "dos trozos -> dos eventos token")
        self.assertEqual(cache.guardados_resumen, 1)
        self.assertEqual(rapid.llamado, 1)

    def test_error_del_motor_se_reporta_sin_romper(self):
        caso = self._caso(rapido=MotorRapidoFalso(falla=True))
        eventos = recolectar(caso.ejecutar(Leccion(url="u", titulo="t", texto="x" * 400)))

        self.assertEqual(eventos[-1].tipo, "error")
        self.assertIn("motor caido", eventos[-1].datos["msg"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
