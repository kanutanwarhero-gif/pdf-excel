import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import easyocr
import numpy as np
import re
from PIL import Image
import io

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Smart AWB to External Order Linker (OCR Enabled)")
st.write("Scanned PDF Shipping Label aur Manifest (CSV) upload karein.")

# Initialize EasyOCR Reader (Hindi/English handle karne ke liye)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

uploaded_pdf = st.file_uploader("1. Scanned Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Data Read Karen
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF to Image Conversion for OCR
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            st.info("🔄 PDF se text read kiya ja raha hai (OCR Running)...")
            
            full_text = ""
            # Har page ko image me convert karke OCR chalayein
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200) # Higher DPI for better OCR accuracy
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # EasyOCR se text extract karein
                ocr_result = reader.readtext(np.array(image), detail=0)
                full_text += " ".join(ocr_result) + " "
            
            # 3. Text me se AWB Number/Tracking Number search karein
            # Hum generic 10 se 15 digit ke numbers search kar rahe hain
            digits = re.findall(r'\b\d{10,15}\b', full_text)
            
            awb_number = None
            if digits:
                # E-commerce formats me aamtaur par pehla bada number AWB hota hai
                awb_number = digits[0]
            
            if awb_number:
                st.info(f"🔍 OCR ko **AWB Number** mila: `{awb_number}`")
                
                # CSV me match karein
                matched_row = df[df['Tracking No_str'].str.contains(str(awb_number), na=False) | (df['Tracking No_str'] == str(awb_number))]
                
                if not matched_row.empty:
                    ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                    st.success(f"🎯 CSV me **Extern Order No** mil gaya: `{ext_order_no}`")
                    
                    # 4. PDF me stamp karein (Pehle page par)
                    page = doc[0]
                    # Note: Yahan location (30, 530) hai, aapki file dekh kar main ise correct kar dunga
                    page.insert_text(fitz.Point(30, 530), f"EXT ORDER: {ext_order_no}", fontsize=12, color=(0, 0, 0))
                    
                    output_pdf_bytes = doc.write()
                    st.download_button(
                        label="📥 Processed PDF Download Karein",
                        data=output_pdf_bytes,
                        file_name=f"Processed_{uploaded_pdf.name}",
                        mime="application/pdf"
                    )
                else:
                    st.error(f"❌ AWB `{awb_number}` CSV ke 'Tracking No' column me nahi mila.")
                    st.write("OCR ko ye saare text mile the:", full_text) # Debugging ke liye
            else:
                st.error("❌ PDF Image se koi AWB Number (10-15 digits) nahi padha ja saka.")
        else:
            st.error("❌ CSV me 'Tracking No' ya 'Extern Order No' headers nahi mile.")
            st.write("Mile hue columns:", list(df.columns))
            
    except Exception as e:
        st.error(f"Error: {e}")

