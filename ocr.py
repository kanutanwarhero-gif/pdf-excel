import zxingcpp

def read_barcode(image):
    results = zxingcpp.read_barcodes(image)

    for r in results:
        if str(r.format) == "Code128":
            return r.text

    return None
