import zxingcpp

def read_barcode(image):
    results = zxingcpp.read_barcodes(image)

    for r in results:
        if "Code 128" in str(r.format) or "Code128" in str(r.format):
            return r.text

    return None
