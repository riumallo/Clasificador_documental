# Clasificador_documental
Clasificador documental que organiza los documentos y obtiene la informacion de ellos.

## Requisitos
- Python 3
- Dependencias Python: `pip install -r requirements.txt`
- Tesseract OCR instalado si usas ese motor

## Configuracion (.env)
Minimo:
```
GOOGLE_APPLICATION_CREDENTIALS=credentials/tu-credencial.json
INPUT_DIR=input_pdfs
OUTPUT_DIR=output
```

Opcionales:
```
OCR_ENGINE=vision|tesseract|auto
OCR_DPI=300
TESSERACT_LANG=spa
TESSERACT_PSM=6
TESSERACT_CONTRAST=1.8
TESSERACT_THRESHOLD=180
TESSERACT_BINARIZE=1
TESSERACT_DESKEW=1
TESSERACT_DESKEW_MAX_ANGLE=5
TESSERACT_DESKEW_STEP=0.5
TESSERACT_DESKEW_SCALE=0.5
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Ejecutar OCR y clasificacion
```
python -m src.main
```

Ejemplos en PowerShell (solo para esa consola):
```
$env:OCR_ENGINE="tesseract"
python -m src.main
```
```
$env:OCR_ENGINE="vision"
python -m src.main
```

Salida:
- Vision: `output/json`
- Tesseract: `output/tesseract_json`

## Clasificar desde JSON existentes
```
python -m src.process_json
```

Para usar los JSON de Tesseract:
```
$env:JSON_DIR_NAME="tesseract_json"
python -m src.process_json
```

Opcionalmente puedes cambiar el nombre del resumen:
```
$env:JSON_SUMMARY_NAME="json_classification_tesseract.txt"
python -m src.process_json
```
