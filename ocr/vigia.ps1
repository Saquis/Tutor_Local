# ============================================================================
#  vigia.ps1 v2 — Mira la pantalla y manda a Telegram SOLO si cambió
# ----------------------------------------------------------------------------
#  Cambios v2:
#    · Solo envía cuando detecta CAMBIO en la pantalla (hash de imagen)
#    · Espera -Intervalo segundos ENTRE envíos (default 11) para dar tiempo a leer
#    · Sigue mirando rápido (cada -Sondeo s) pero solo emite si hay novedad
#
#  Uso:
#     powershell -File vigia.ps1                          (1 mirada)
#     powershell -File vigia.ps1 -Repetir 500 -Intervalo 11 -Sondeo 3
# ============================================================================
param(
    [int]$Repetir = 1,
    [int]$Intervalo = 11,   # segundos de espera ENTRE envíos a Telegram
    [int]$Sondeo = 3        # segundos entre capturas de sondeo
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$base   = "C:\Users\RYZEN 5 GAMER"
$tgFile = Join-Path $base ".tutor-tg.key"
$dsFile = Join-Path $base "Tutor_Local\servidor\deepseek.key"
$capDir = Join-Path $base "Tutor_Local\ocr\capturas"
if (-not (Test-Path $capDir)) { New-Item -ItemType Directory -Path $capDir -Force | Out-Null }

$tg   = Get-Content $tgFile
$bot  = $tg[0].Trim()
$chat = $tg[1].Trim()
$dsk  = (Get-Content $dsFile -Raw).Trim()

$sys = "Mira la pantalla. Si hay una pregunta, RESPONDELA directo, en espanol, sin explicar y sin describir la pantalla. Si es de opcion multiple responde: 'Respuesta: <LETRA> - <texto>'. Si es abierta, responde en una sola frase clara. Si hay codigo, di solo el error y la correccion. Nada mas."
$ask = "Responde la pregunta que aparece en pantalla. Solo la respuesta."

function Enviar-Telegram([string]$texto) {
    $h = @{ "Authorization" = ("Bea" + "rer " + $bot) }
    $b = @{ chat_id = $chat; text = $texto; parse_mode = "Markdown" }
    try { Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $bot + "/sendMessage") -Method Post -Headers $h -Body $b -TimeoutSec 30 | Out-Null }
    catch { try { $b.Remove("parse_mode"); Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $bot + "/sendMessage") -Method Post -Headers $h -Body $b -TimeoutSec 30 | Out-Null } catch {} }
}

function Capturar([string]$ruta) {
    $s = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $s.Width, $s.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($s.Location, [System.Drawing.Point]::Empty, $s.Size)
    $g.Dispose()
    $bmp.Save($ruta, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

function HashArchivo([string]$ruta) {
    $fs = [System.IO.File]::OpenRead($ruta)
    try {
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $hash = $md5.ComputeHash($fs)
        return ([System.BitConverter]::ToString($hash) -replace '-', '')
    } finally { $fs.Close() }
}

$enviados = 0
$ultimoHash = ""
$ultimoEnvio = [datetime]::MinValue
$marca = Get-Date -Format "HH:mm:ss"
Write-Output "[$marca] vigia v2 iniciado (cambio-only, intervalo ${Intervalo}s, sondeo ${Sondeo}s)"

for ($r = 0; $r -lt $Repetir; $r++) {

    # comprobamos si toca enviar (respetando el intervalo de 11s)
    $desdeUltimo = ((Get-Date) - $ultimoEnvio).TotalSeconds
    if ($desdeUltimo -lt $Intervalo) {
        Start-Sleep -Seconds $Sondeo
        continue
    }

    $tmp = Join-Path $capDir ("vigia_tmp.png")
    Capturar $tmp
    $hash = HashArchivo $tmp

    # ¿cambió la pantalla?
    if ($hash -eq $ultimoHash) {
        Remove-Item $tmp -ErrorAction SilentlyContinue
        Start-Sleep -Seconds $Sondeo
        continue
    }

    # cambió → analizar y enviar
    $marca = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $img = Join-Path $capDir ("vigia_$marca.png")
    Move-Item -Path $tmp -Destination $img -Force

    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($img))
    $cuerpo = @{
        model = "deepseek-flash"
        max_tokens = 2000
        temperature = 0.2
        thinking = @{ type = "disabled" }
        messages = @(
            @{ role = "system"; content = $sys },
            @{ role = "user"; content = @(
                @{ type = "text"; text = $ask },
                @{ type = "image_url"; image_url = @{ url = ("data:image/png;base64," + $b64) } }
            ) }
        )
    } | ConvertTo-Json -Depth 12 -Compress

    try {
        $h = @{ "Authorization" = ("Bea" + "rer " + $dsk) }
        $resp = Invoke-RestMethod -Uri "https://api.deepseek.com/chat/completions" -Method Post -Headers $h -ContentType "application/json" -Body $cuerpo -TimeoutSec 90
        $txt = $resp.choices[0].message.content
        if ([string]::IsNullOrWhiteSpace($txt)) { $txt = "(respuesta vacia)" }
    } catch {
        $txt = "Error al consultar el modelo: " + $_.Exception.Message
    }

    Enviar-Telegram $txt
    $enviados++
    $ultimoHash = $hash
    $ultimoEnvio = Get-Date
    $hora = (Get-Date).ToString("HH:mm:ss")
    Write-Output "[$hora] enviado #$enviados"

    Remove-Item $img -ErrorAction SilentlyContinue
    Start-Sleep -Seconds $Sondeo
}

$fin = (Get-Date).ToString("HH:mm:ss")
Write-Output "[$fin] fin. total enviados: $enviados"
