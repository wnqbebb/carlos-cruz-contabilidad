# Deja el lector de fotos (Tesseract OCR) listo dentro de la aplicación:
#   datos_app\tesseract\  -> tesseract.exe y sus DLL (sin las herramientas de entrenamiento)
#   datos_app\tessdata\   -> español, inglés y orientación (osd)
# Lo usan iniciar.bat (primera vez) y empaquetar\construir.bat (el .exe lo lleva dentro).
# Si falla, la aplicación sigue funcionando; solo la lectura de FOTOS de renta queda sin OCR.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz "datos_app\tesseract"
$idiomas = Join-Path $raiz "datos_app\tessdata"
New-Item -ItemType Directory -Force $destino, $idiomas | Out-Null

function Buscar-Tesseract {
  $candidatos = @(
    "$env:ProgramFiles\Tesseract-OCR\tesseract.exe",
    "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe",
    "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe"
  )
  foreach ($c in $candidatos) { if ($c -and (Test-Path $c)) { return $c } }
  $enRuta = Get-Command tesseract.exe -ErrorAction SilentlyContinue
  if ($enRuta) { return $enRuta.Source }
  return $null
}

if (-not (Test-Path (Join-Path $destino "tesseract.exe"))) {
  $exe = Buscar-Tesseract
  if (-not $exe -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando el lector de fotos (Tesseract OCR)..."
    winget install --id UB-Mannheim.TesseractOCR -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
    $exe = Buscar-Tesseract
  }
  if (-not $exe) {
    Write-Host "[AVISO] No se encontro Tesseract OCR. La renta funciona con PDF y Excel; para leer FOTOS instale"
    Write-Host "        Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) y vuelva a ejecutar iniciar.bat."
    exit 0
  }
  $origen = Split-Path -Parent $exe
  Copy-Item (Join-Path $origen "tesseract.exe") $destino -Force
  Get-ChildItem $origen -Filter *.dll | Copy-Item -Destination $destino -Force
  Write-Host "Lector de fotos copiado a datos_app\tesseract"
}

$fuentes = @{
  "spa.traineddata" = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/spa.traineddata"
  "eng.traineddata" = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata"
  "osd.traineddata" = "https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata"
}
foreach ($nombre in $fuentes.Keys) {
  $archivo = Join-Path $idiomas $nombre
  if (-not (Test-Path $archivo)) {
    Write-Host "Descargando $nombre..."
    Invoke-WebRequest -UseBasicParsing -Uri $fuentes[$nombre] -OutFile $archivo
  }
}
Write-Host "Lector de fotos listo."
