# ============================================================================
#  bucle_captura.ps1 — Captura automatica cada N segundos (estilo Logbook)
# ----------------------------------------------------------------------------
#  Captura la pantalla principal cada 30 s y guarda un JPEG pequeno.
#  Mantiene solo los ultimos N archivos (por defecto 60 = 30 minutos).
#
#  NO envia nada a Internet. Solo escribe archivos locales.
#
#  Uso:  powershell -File bucle_captura.ps1
#        (o doble clic en  iniciar_logbook.bat)
#
#  Detener: cerrar la ventana, o crear el archivo  logbook\DETENER
# ============================================================================

param(
    [int]$IntervaloSegundos = 30,
    [int]$MaxFrames         = 60,
    [int]$IndicePantalla    = 0,
    [int]$AnchoMaximo       = 1440,
    [int]$CalidadJPEG       = 60
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$Base    = $PSScriptRoot
$Carpeta = Join-Path $Base "frames"
$Parar   = Join-Path $Base "DETENER"
$Log     = Join-Path $Base "logbook.log"

if (-not (Test-Path $Carpeta)) { New-Item -ItemType Directory -Path $Carpeta -Force | Out-Null }
if (Test-Path $Parar) { Remove-Item $Parar -Force }

# Codificador JPEG
$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
         Where-Object { $_.MimeType -eq 'image/jpeg' }
$params = New-Object System.Drawing.Imaging.EncoderParameters 1
$params.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
    [System.Drawing.Imaging.Encoder]::Quality, [long]$CalidadJPEG)

function Escribir-Log($msg) {
    $linea = "$(Get-Date -Format 'HH:mm:ss')  $msg"
    Add-Content -Path $Log -Value $linea
    Write-Host $linea
}

Escribir-Log "=== Logbook iniciado · cada ${IntervaloSegundos}s · max $MaxFrames frames ==="

$anteriorHash = ""
$contador = 0

while (-not (Test-Path $Parar)) {

    try {
        $pantallas = [System.Windows.Forms.Screen]::AllScreens
        $p = $pantallas[[Math]::Min($IndicePantalla, $pantallas.Count - 1)]
        $b = $p.Bounds

        $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
        $g.Dispose()

        # Redimensionar si excede el ancho maximo (menos bytes = menos costo)
        if ($bmp.Width -gt $AnchoMaximo) {
            $escala = $AnchoMaximo / $bmp.Width
            $nuevo = New-Object System.Drawing.Bitmap $AnchoMaximo, ([int]($bmp.Height * $escala))
            $g2 = [System.Drawing.Graphics]::FromImage($nuevo)
            $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $g2.DrawImage($bmp, 0, 0, $nuevo.Width, $nuevo.Height)
            $g2.Dispose(); $bmp.Dispose(); $bmp = $nuevo
        }

        # Huella rapida para saltar frames identicos (no gastar en analisis)
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $bytes = $ms.ToArray(); $ms.Dispose()
        $hash = [System.BitConverter]::ToString(
            [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)).Substring(0, 16)

        if ($hash -ne $anteriorHash) {
            $nombre = "frame_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".jpg"
            [System.IO.File]::WriteAllBytes((Join-Path $Carpeta $nombre), $bytes)
            $anteriorHash = $hash
            $contador++
            Escribir-Log "frame $contador  $nombre  ($([math]::Round($bytes.Length/1KB,1)) KB)"
        }

        $bmp.Dispose()

        # Poda: conservar solo los ultimos MaxFrames
        $todos = Get-ChildItem -Path $Carpeta -Filter "frame_*.jpg" | Sort-Object Name
        if ($todos.Count -gt $MaxFrames) {
            $todos | Select-Object -First ($todos.Count - $MaxFrames) | Remove-Item -Force
        }
    }
    catch {
        Escribir-Log "ERROR: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $IntervaloSegundos
}

Escribir-Log "=== Logbook detenido (archivo DETENER encontrado) ==="
