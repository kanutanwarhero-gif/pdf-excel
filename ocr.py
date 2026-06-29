import zxingcpp

def read_barcode(image):

    result = zxingcpp.read_barcode(image)

    if result is None:
        return None

    return result.text
