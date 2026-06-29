import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
import re
from PIL import Image
import io

# Tesseract path config (Streamlit Linux server ke liye)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Bulk AWB to External Order Linker")
st.write("Multi-page Scanned PDF aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Scanned Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read Karen
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open Karen
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"🔄 Total {total_pages} pages process ho rhe hain, kripya thoda intezar karein...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            match_count = 0
            
            # Har page par alag se loop chalayein
            for page_num in range(total_pages):
                status_text.text(f"Processing page {page_num + 1} of {total_pages}...")
                page = doc[page_num]
                
                # Image render karein OCR ke liye
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Fast OCR se text extract karein
                page_text = pytesseract.image_to_string(img)
                
                # 10-15 digit ka AWB/Tracking number search karein
                digits = re.findall(r'\b\d{10,15}\b', page_text)
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                awb_number = None
                if awb_match:
                    awb_number = awb_match.group(1)
                elif digits:
                    awb_number = digits[0]
                
                if awb_number:
                    # CSV me match karein
                    matched_row = df[df['Tracking No_str'] == str(awb_number)]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_str'].str.contains(str(awb_number), na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Only Order ID print karni h
                        text_to_print = f"{ext_order_no}"
                        
                        # "amazon shipping" ke right side ke liye coordinates:
                        # X=280 (thoda right me), Y=45 (top bar ki line me)
                        # Font: helv-bold (Standard Helvetica Bold font)
                        # Font size: 14 (thoda bada aur clear dikhne ke liye)
                        position = fitz.Point(280, 45)
                        
                        page.insert_text(
                            position, 
                            text_to_print, 
                            fontsize=14, 
                            fontname="helv-bold", 
                            color=(0, 0, 0)
                        )
                        match_count += 1
                
                # Progress bar update karein
                progress_bar.progress((page_num + 1) / total_pages)
            
            status_text.text(f"✅ Processing Complete! Total Matches: {match_count}/{total_pages}")
            
            # 4. Final PDF output download ke liye taiyar karein
            output_pdf_bytes = doc.write()
            st.download_button(
                label="📥 All Processed Pages PDF Download Karein",
                data=output_pdf_bytes,
                file_name=f"Processed_Bulk_{uploaded_pdf.name}",
                mime="application/pdf"
              
            )
        else:
            st.error("❌ CSV Columns headers miss-matched hain. 'Tracking No' aur 'Extern Order No' check karein.")
            
    except Exception as e:
        st.error(f"Error: {e}")

