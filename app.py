import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
import re
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Perfect AWB Matcher (Regex Fix)")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # CSV Read
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            # Clean CSV column (Har tarah ke formats, .0 decimal, spaces clear karne ke liye)
            df['Tracking No_clean'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"🔄 Scanning {total_pages} pages...")
            match_count = 0
            debug_info = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Image at 150 DPI for stable RAM usage
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # Full page text extract with standard layout retention
                page_text = pytesseract.image_to_string(img)
                
                # --- STRICT REGEX LOGIC FOR AWB ---
                # Yeh sirf 'AWB' word ke baad wale 10-15 digits ko hi target karega (Pin codes ko chhod dega)
                awb_number = None
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d{10,15})', page_text, re.IGNORECASE)
                
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                else:
                    # Fallback: Agar text me 'AWB' misread ho, toh pure page me se sirf 11 to 14 digit ka number uthaye
                    # Pin codes 6 digit ke hote hain, toh \d{11,14} unhe automatic filter kar dega
                    digits = re.findall(r'\b\d{11,14}\b', page_text)
                    if digits:
                        awb_number = digits[0].strip()
                
                if awb_number:
                    awb_clean = str(awb_number).strip()
                    
                    # Match clean numbers
                    matched_row = df[df['Tracking No_clean'] == awb_clean]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_clean'].str.contains(awb_clean, na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Right side of Amazon Shipping
                        position = fitz.Point(280, 45)
                        page.insert_text(position, ext_order_no, fontsize=14, fontname="helv-bold", color=(0, 0, 0))
                        match_count += 1
                        
                        if page_num < 5:
                            debug_info.append(f"✅ Page {page_num+1}: Clean AWB `{awb_clean}` -> Order `{ext_order_no}`")
                    else:
                        if page_num < 5:
                            debug_info.append(f"❌ Page {page_num+1}: AWB `{awb_clean}` mila, par CSV me nahi mila.")
                else:
                    if page_num < 5:
                        # Debug text snippet to check what OCR is actually reading
                        snippet = page_text.replace('\n', ' ')[:50]
                        debug_info.append(f"⚠️ Page {page_num+1}: AWB number format nahi mila. OCR Text Snippet: [{snippet}]")
            
            st.subheader("📋 Execution Logs (Top 5 Pages)")
            for log in debug_info:
                st.write(log)
                
            if match_count > 0:
                st.success(f"🎯 Total Matched: {match_count}/{total_pages}")
                st.download_button(
                    label="📥 Processed PDF Download",
                    data=doc.write(),
                    file_name="Processed_Final.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ 0 Matches found. Ek baar upar ke debug snippets check karein.")
        else:
            st.error("❌ CSV columns missing ('Tracking No' / 'Extern Order No')")
    except Exception as e:
        st.error(f"Error: {e}")

