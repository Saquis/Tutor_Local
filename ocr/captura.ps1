# ============================================================================
#  captura.ps1 — Captura la pantalla para que el asistente la vea
# ----------------------------------------------------------------------------
#  Uso:  doble clic en  captura.bat   (o ejecutar este script)
#  Guarda un PNG en  capturas\  con fecha y hora.
#  NO envia nada a Internet: solo escribe un archivo local.
# ============================================================================

param(
    [string]$Destino = "",
    [switch]$Todas
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Carpeta de salida
if ([string]::IsNullOrWhiteSpace($Destino)) {
    $Destino = Join-Path $PSScriptRoot "capturas"
}
if (-not (Test-Path $Destino)) {
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
}

# Por defecto: SOLO la pantalla PRINCIPAL (ahorra ~50% de tokens).
# Con -Todas se capturan todos los monitores.
if ($Todas) {
    $pantallas = [System.Windows.Forms.Screen]::AllScreens
} else {
    $pantallas = @([System.Windows.Forms.Screen]::PrimaryScreen)
}
$marca = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host ""
Write-Host "  Capturando pantalla..." -ForegroundColor Cyan

$i = 0
foreach ($p in $pantallas) {
    $b = $p.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $g.Dispose()

    $sufijo = if ($pantallas.Count -gt 1) { "_pantalla$i" } else { "" }
    $ruta = Join-Path $Destino "captura_${marca}${sufijo}.png"
    $bmp.Save($ruta, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()

    $kb = [math]::Round((Get-Item $ruta).Length / 1KB, 1)
    Write-Host "  OK  $ruta  ($kb KB)" -ForegroundColor Green
    $i++
}

Write-Host ""
Write-Host "  Listo. Dile al asistente: 'mira la captura'." -ForegroundColor Yellow
Write-Host ""
Start-Sleep -Seconds 2
