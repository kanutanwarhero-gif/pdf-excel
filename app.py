import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
import re
from PIL import Image
import io

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Fast Image OCR AWB Linker")
st.write("Scanned Image PDF Label aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Scanned Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read Karen
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF to Image Conversion & OCR
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            st.info("🔄 Scanned Image se AWB read kiya ja raha hai...")
            
            full_text = ""
            for page in doc:
                # 200 DPI par render kar rahe hain taaki image clear ho aur OCR jaldi ho
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Tesseract OCR call (Fast text extraction)
                page_text = pytesseract.image_to_string(img)
                full_text += page_text + "\n"
            
            # 3. Text se 10-15 digit ka AWB number nikalein
            # Amazon Shipping labels par 10-12 ya 15 digits ka number hota hai (e.g., 168063721758)
            digits = re.findall(r'\b\d{10,15}\b', full_text)
            
            # Agar 'AWB' text ke paas wala number chahiye toh pehle woh try karte hain
            awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', full_text, re.IGNORECASE)
            
            if awb_match:
                awb_number = awb_match.group(1)
            elif digits:
                awb_number = digits[0]
            else:
                awb_number = None
                
            if awb_number:
                st.info(f"🔍 OCR ko **AWB Number** mila: `{awb_number}`")
                
                # CSV me matching
                matched_row = df[df['Tracking No_str'] == str(awb_number)]
                if matched_row.empty:
                    matched_row = df[df['Tracking No_str'].str.contains(str(awb_number), na=False)]
                    
                if not matched_row.empty:
                    ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                    st.success(f"🎯 Match Mil Gaya! **Extern Order No**: `{ext_order_no}`")
                    
                    # 4. PDF Image ke upar text write karein
                    page = doc[0]
                    
                    # Red boxes ki positions par text stamp kar rahe hain
                    # Top blank box approx position
                    page.insert_text(fitz.Point(20, 335), f"EXT ORDER: {ext_order_no}", fontsize=12, color=(0, 0, 0))
                    # Bottom blank box approx position
                    page.insert_text(fitz.Point(20, 955), f"EXT ORDER: {ext_order_no}", fontsize=12, color=(0, 0, 0))
                    
                    output_pdf_bytes = doc.write()
                    st.download_button(
                        label="📥 Processed PDF Download Karein",
                        data=output_pdf_bytes,
                        file_name=f"Processed_{uploaded_pdf.name}",
                        mime="application/pdf"
                    )
                else:
                    st.error(f"❌ AWB `{awb_number}` CSV me nahi mila.")
            else:
                st.error("❌ Image me se koi 10-15 digit ka AWB number detect nahi hua.")
        else:
            st.error("❌ CSV Columns headers miss-matched hain.")
            
    except Exception as e:
        st.error(f"Error: {e}")

