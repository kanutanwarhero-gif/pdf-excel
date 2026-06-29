import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
import re
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Final Verified AWB Matcher")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_clean'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"🔄 High-Quality Scan Running for {total_pages} pages...")
            match_count = 0
            debug_info = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # DPI 300 kar diya h taaki barcode ke niche ka chhota text clear read ho sake
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # Layout setting --psm 3 (Standard automatic layout analysis)
                page_text = pytesseract.image_to_string(img, config='--oem 3 --psm 3')
                
                # --- STRIP ALL SPACES FOR MATCHING ---
                # Text me se saare spaces hatayein taaki exact long digit string mile
                flattened_text = re.sub(r'\s+', '', page_text)
                
                # 11 se 15 digit ka tracking number extract karein
                digits = re.findall(r'\d{11,15}', flattened_text)
                
                awb_clean = None
                if digits:
                    # Amazon shipping standard tracking 168... se shuru hoti h, check matrix
                    for d in digits:
                        if d.startswith('168') or len(d) == 12:
                            awb_clean = d
                            break
                    if not awb_clean:
                        awb_clean = digits[0]
                
                if awb_clean:
                    matched_row = df[df['Tracking No_clean'] == awb_clean]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_clean'].str.contains(awb_clean, na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Right side of Amazon Shipping top text
                        position = fitz.Point(280, 45)
                        page.insert_text(position, ext_order_no, fontsize=14, fontname="helv-bold", color=(0, 0, 0))
                        match_count += 1
                        
                        if page_num < 3:
                            debug_info.append(f"✅ Page {page_num+1}: AWB `{awb_clean}` -> Ext Order `{ext_order_no}`")
                    else:
                        if page_num < 3:
                            debug_info.append(f"❌ Page {page_num+1}: AWB `{awb_clean}` extracted but not found in CSV.")
                else:
                    if page_num < 3:
                        debug_info.append(f"⚠️ Page {page_num+1}: Tracking number text bypass ho gya.")
            
            st.subheader("📋 Status Logs")
            for log in debug_info:
                st.write(log)
                
            if match_count > 0:
                st.success(f"🎯 Successful Matches: {match_count}/{total_pages}")
                st.download_button(
                    label="📥 Processed PDF Download",
                    data=doc.write(),
                    file_name="Processed_Final.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Matches abhi bhi 0 hain.")
        else:
            st.error("❌ CSV columns check karein.")
    except Exception as e:
        st.error(f"Error: {e}")

