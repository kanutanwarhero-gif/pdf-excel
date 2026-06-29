import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Ultra-Fast AWB to External Order Linker")
st.write("Multi-page PDF aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read Karen
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            # CSV ke tracking numbers ko string me cleanly convert karein
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open Karen
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"⚡ Fast processing shuru... Total {total_pages} pages hain.")
            
            match_count = 0
            
            # Har page par fast text search loop
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Direct text extract (No OCR, No Image Conversion - Instant)
                page_text = page.get_text("text")
                
                # Agar simple text block na mile toh blocks layout try karein
                if not page_text.strip():
                    blocks = page.get_text("blocks")
                    page_text = "\n".join([b[4] for b in blocks if isinstance(b[4], str)])
                
                # --- AWB Extraction Logic ---
                awb_number = None
                
                # Pattern 1: AWB word ke baad digits dhundein
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                else:
                    # Pattern 2: Agar 'AWB' na mile toh 11-15 digit ka serial number filter karein
                    digits = re.findall(r'\b\d{11,15}\b', page_text)
                    if digits:
                        awb_number = digits[0].strip()
                
                if awb_number:
                    # CSV me match check karein
                    matched_row = df[df['Tracking No_str'] == str(awb_number)]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_str'].str.contains(str(awb_number), na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Amazon Shipping ke right side me stamp karne ke liye coordinates:
                        # X=280, Y=45 (Helvetica Bold, font size 14)
                        position = fitz.Point(280, 45)
                        
                        page.insert_text(
                            position, 
                            ext_order_no, 
                            fontsize=14, 
                            fontname="helv-bold", 
                            color=(0, 0, 0)
                        )
                        match_count += 1
            
            st.success(f"🎯 Processing Complete! Total Successful Matches: {match_count}/{total_pages}")
            
            # 3. Final Output PDF taiyar karein
            output_pdf_bytes = doc.write()
            st.download_button(
                label="📥 All Processed Pages PDF Download Karein",
                data=output_pdf_bytes,
                file_name=f"Processed_Labels.pdf",
                mime="application/pdf"
            )
        else:
            st.error("❌ CSV me 'Tracking No' ya 'Extern Order No' headers nahi mile. Kripya verification karein.")
            
    except Exception as e:
        st.error(f"Error occurred: {e}")

