import zxingcpp

def read_barcode(image):
    results = zxingcpp.read_barcodes(image)

    if not results:
        return "No barcode found"

    output = []

    for r in results:
        output.append(f"{r.format} -> {r.text}")

    return " | ".join(output)
