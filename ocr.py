import zxingcpp

def read_barcode(image):
    results = zxingcpp.read_barcodes(image)

    for r in results:
        print(r.format, r.text)

    return None
