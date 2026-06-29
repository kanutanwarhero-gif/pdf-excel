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
st.title("📦 Final Super-Stitch AWB Linker")
st.write("Multi-page PDF aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read & Clean
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"🔄 Scanning {total_pages} pages dynamically...")
            
            match_count = 0
            debug_info = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Low DPI (150) taaki server par RAM load na bade aur process quick ho
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                width, height = img.size
                
                # --- EXACT AWB & BARCODE ZONE CROP ---
                # Pure page ko chhod kar sirf AWB text wale specific vertical band ko crop karenge
                # Taaki address ke pin codes scan hi na ho sakein
                left = int(width * 0.10)
                top_crop = int(height * 0.45)
                right = int(width * 0.90)
                bottom = int(height * 0.75)
                
                cropped_img = img.crop((left, top_crop, right, bottom))
                
                # Strict Digit Filter config taaki system sirf AWB numbers target kare
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789AWBawb: '
                page_text = pytesseract.image_to_string(cropped_img, config=custom_config)
                
                # Fallback: Agar crop zone me kuch miss ho jaye
                if not any(char.isdigit() for char in page_text):
                    page_text = pytesseract.image_to_string(img, config=custom_config)
                
                # Clean text to extract exact AWB number
                awb_number = None
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                else:
                    # Agar 'AWB' text misread ho par 11-13 digit ka clean number dikhe
                    digits = re.findall(r'\b\d{11,14}\b', page_text)
                    if digits:
                        awb_number = digits[0].strip()
                
                if awb_number:
                    awb_clean = str(awb_number).strip()
                    
                    # Match in CSV
                    matched_row = df[df['Tracking No_str'] == awb_clean]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_str'].str.contains(awb_clean, na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Amazon Shipping ke right side me stamp position
                        position = fitz.Point(280, 45)
                        page.insert_text(
                            position, 
                            ext_order_no, 
                            fontsize=14, 
                            fontname="helv-bold", 
                            color=(0, 0, 0)
                        )
                        match_count += 1
                        if page_num < 5:
                            debug_info.append(f"✅ Page {page_num+1}: Clean AWB `{awb_clean}` matched with `{ext_order_no}`")
                    else:
                        if page_num < 5:
                            debug_info.append(f"❌ Page {page_num+1}: OCR read AWB `{awb_clean}`, but not found in CSV.")
                else:
                    if page_num < 5:
                        debug_info.append(f"⚠️ Page {page_num+1}: Could not capture AWB format.")
            
            # Print Logs
            st.subheader("📋 Final Run Logs (Top 5 Pages)")
            for log in debug_info:
                st.write(log)
                
            if match_count > 0:
                st.success(f"🎯 Boom! Total Successful Matches: {match_count}/{total_pages}")
                output_pdf_bytes = doc.write()
                st.download_button(
                    label="📥 All Processed Pages PDF Download Karein",
                    data=output_pdf_bytes,
                    file_name=f"Processed_Labels_Final.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Abhi bhi matching nahi hui. Ek baar upar ke logs me AWB numbers check karein.")
        else:
            st.error("❌ CSV headers matched nahi hain.")
    except Exception as e:
        st.error(f"Error: {e}")

