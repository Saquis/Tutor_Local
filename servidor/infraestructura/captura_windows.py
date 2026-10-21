"""Adaptador: captura de pantalla en Windows.

Implementa el puerto CapturaPantalla. Llama al script de PowerShell que ya
existe en `ocr/captura.ps1`, que captura TODAS las pantallas.

Por qué PowerShell y no una librería de Python:
- No añade dependencias (nada de pyautogui/Pillow).
- El script ya está probado.
- Funciona con multi-monitor.

OJO: se ejecuta UNA captura por llamada. Un bucle continuo lo bloquea el
antivirus (un loop de captura de pantalla = firma de spyware).
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResultadoCaptura:
    rutas: list[Path]
    ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.rutas)


class CapturaWindows:
    """Implementa CapturaPantalla llamando al script de PowerShell."""

    def __init__(
        self,
        script: str | Path = r"C:\Users\RYZEN 5 GAMER\Tutor_Local\ocr\captura.ps1",
        destino_script: str | Path = r"C:\Users\RYZEN 5 GAMER\Tutor_Local\ocr\capturas",
        destino_local: str | Path | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.script = Path(script)
        self.destino_script = Path(destino_script)
        # Copia local: el servidor lee desde aquí (más rápido y sin rutas de Windows)
        self.destino_local = Path(destino_local) if destino_local else self.destino_script
        self.timeout = timeout

    def capturar(self) -> ResultadoCaptura:
        import time

        if not self.script.exists():
            return ResultadoCaptura([], 0, error=f"no existe el script {self.script}")

        # Limpiar capturas viejas
        try:
            for viejo in self.destino_script.glob("*.png"):
                viejo.unlink(missing_ok=True)
        except OSError:
            pass

        t0 = time.perf_counter()
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(self.script)],
                capture_output=True, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return ResultadoCaptura([], 0, error="la captura tardó demasiado")
        except FileNotFoundError:
            return ResultadoCaptura([], 0, error="no se encontró powershell.exe")
        except Exception as exc:  # noqa: BLE001
            return ResultadoCaptura([], 0, error=f"{type(exc).__name__}: {exc}")

        ms = int((time.perf_counter() - t0) * 1000)
        nuevas = sorted(self.destino_script.glob("captura_*.png"), key=lambda p: p.name)

        # Copiar a la ruta local si hace falta
        if self.destino_local != self.destino_script:
            for viejo in self.destino_local.glob("*.png"):
                viejo.unlink(missing_ok=True)
            copiadas = []
            for p in nuevas:
                destino = self.destino_local / p.name
                try:
                    shutil.copy2(p, destino)
                    copiadas.append(destino)
                except OSError:
                    copiadas.append(p)
            nuevas = copiadas

        if not nuevas:
            return ResultadoCaptura([], ms, error="no se generó ninguna captura")
        return ResultadoCaptura(nuevas, ms)
