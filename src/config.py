import os
from dotenv import load_dotenv

load_dotenv()

GCP_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

if not GCP_CREDENTIALS or not os.path.exists(GCP_CREDENTIALS):
    raise RuntimeError(" No se encontró el JSON de Google Vision")

if not INPUT_DIR or not OUTPUT_DIR:
    raise RuntimeError(" INPUT_DIR o OUTPUT_DIR no definidos")
