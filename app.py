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
st.title("📦 Perfect Bulk AWB to External Order Linker")
st.write("Multi-page Scanned PDF aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Scanned Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read Karen
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            # Clean tracking numbers
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
                
                # High DPI par page render karein taaki text clear dikhe
                pix = page.get_pixmap(dpi=200)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                width, height = img.size
                
                # --- SMART CROP FOR AWB ZONE ---
                # Amazon label me AWB middle se bottom ke beech me hota h (40% se 85% height tak)
                # Pure page ka noise (jaise top pin code ya address) cut karne ke liye crop area:
                left = int(width * 0.05)
                top_crop = int(height * 0.40)
                right = int(width * 0.95)
                bottom = int(height * 0.85)
                
                cropped_img = img.crop((left, top_crop, right, bottom))
                
                # Tesseract OCR sirf is cropped zone par chalayein (Keval digits read karne ki setting ke sath)
                # custom_config se OCR sirf digits aur space dhundega jo speed aur accuracy badha dega
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789AWBawb:_-'
                page_text = pytesseract.image_to_string(cropped_img, config=custom_config)
                
                # Pure page ka backup text agar crop me na mile (Fallback)
                if not any(char.isdigit() for char in page_text):
                    page_text = pytesseract.image_to_string(img)
                
                # 10-15 digit ka AWB/Tracking number search karein
                digits = re.findall(r'\b\d{10,15}\b', page_text)
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                awb_number = None
                if awb_match:
                    awb_number = awb_match.group(1)
                elif digits:
                    # Agar multi-digits milein toh sabse bada number ya pehla sahi length ka filter karein
                    for d in digits:
                        if len(d) >= 11:  # Amazon AWB aamtaur par 12-14 digits ka hota h
                            awb_number = d
                            break
                    if not awb_number:
                        awb_number = digits[0]
                
                if awb_number:
                    # CSV me match karein
                    matched_row = df[df['Tracking No_str'] == str(awb_number)]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_str'].str.contains(str(awb_number), na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Amazon Shipping ke bilkul right me blank space par print karne ke liye:
                        # X=280 (Right shift), Y=45 (Top header line)
                        # Font size=14 aur Font style=helv-bold
                        position = fitz.Point(280, 45)
                        
                        page.insert_text(
                            position, 
                            ext_order_no, 
                            fontsize=14, 
                            fontname="helv-bold", 
                            color=(0, 0, 0)
                        )
                        match_count += 1
                
                # Progress bar update
                progress_bar.progress((page_num + 1) / total_pages)
            
            status_text.text(f"✅ Processing Complete! Successfully Matched: {match_count}/{total_pages}")
            
            # 4. Final PDF output
            output_pdf_bytes = doc.write()
            st.download_button(
                label="📥 All Processed Pages PDF Download Karein",
                data=output_pdf_bytes,
                file_name=f"Processed_Bulk_Labels.pdf",
                mime="application/pdf"
            )
        else:
            st.error("❌ CSV me 'Tracking No' ya 'Extern Order No' headers nahi mile.")
            
    except Exception as e:
        st.error(f"Error: {e}")

