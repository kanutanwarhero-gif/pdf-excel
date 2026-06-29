import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Fast AWB to External Order Linker")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Data Read aur Clean
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_clean'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"⚡ Processing {total_pages} pages instantly...")
            match_count = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text("text")
                
                if not page_text.strip():
                    blocks = page.get_text("blocks")
                    page_text = "\n".join([b[4] for b in blocks if isinstance(b[4], str)])
                
                # AWB Number Extract Logic
                awb_number = None
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                else:
                    digits = re.findall(r'\b\d{11,14}\b', page_text)
                    if digits:
                        awb_number = digits[0].strip()
                
                if awb_number:
                    awb_clean = str(awb_number).strip()
                    
                    # CSV Matching
                    matched_row = df[df['Tracking No_clean'] == awb_clean]
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_clean'].str.contains(awb_clean, na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # --- SAFE TEXT INSERTION ---
                        # X=280, Y=45 (Amazon Shipping ke right me blank space)
                        # Bina kisi structural width ya border dependency ke pure text overlay
                        page.insert_text(
                            fitz.Point(280, 45), 
                            ext_order_no, 
                            fontsize=16, 
                            fontname="helv",  # Standard core font
                            color=(0, 0, 0)
                        )
                        match_count += 1
            
            if match_count > 0:
                st.success(f"🎯 Success! Total Matched Labels: {match_count}/{total_pages}")
                st.download_button(
                    label="📥 Processed PDF Download",
                    data=doc.write(),
                    file_name="Processed_Labels_Final.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ PDF read ho gaya par CSV data se koi match nahi mila.")
        else:
            st.error("❌ CSV headers galat hain. Kripya 'Tracking No' aur 'Extern Order No' check karein.")
    except Exception as e:
        st.error(f"Error occurred: {e}")

