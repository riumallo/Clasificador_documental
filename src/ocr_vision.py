from google.cloud import vision

def ocr_image_bytes_vision(png_bytes: bytes) -> str:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=png_bytes)

    # document_text_detection suele ir mejor para documentos
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Google Vision error: {response.error.message}")

    annotation = response.full_text_annotation
    return (annotation.text or "").strip()
