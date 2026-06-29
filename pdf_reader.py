import fitz
from PIL import Image
import io

def pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)

    images = []

    for page in doc:

        pix = page.get_pixmap(matrix=fitz.Matrix(3,3))

        img = Image.open(io.BytesIO(pix.tobytes("png")))

        images.append(img)

    return images
