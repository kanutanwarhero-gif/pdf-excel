import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Final Verified AWB Matcher")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read & Clean
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            # Tracking numbers ko cleanly string me convert karein
            df['Tracking No_clean'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open (Direct text-based extraction for instant speed)
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"⚡ Processing {total_pages} pages instantly...")
            match_count = 0
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Direct text layers read karna bina kisi image/OCR ke load ke
                page_text = page.get_text("text")
                
                # Agar simple text khali aaye toh blocks layout extraction fallback
                if not page_text.strip():
                    blocks = page.get_text("blocks")
                    page_text = "\n".join([b[4] for b in blocks if isinstance(b[4], str)])
                
                # --- AWB Search Logic ---
                awb_number = None
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                else:
                    # Agar 'AWB' text block me alag ho toh 11-14 digit ka single string fetch karein
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
                        
                        # --- FIX: GAYAB KIYA EXTERNAL FONT DEPENDENCY ---
                        # Hum default font ('helv') use kar rahe hain bina fontname argument ke, font file crash se bachne ke liye
                        # Size badha kar 16 kiya h taaki bina bold ke bhi door se bada aur clear dikhe
                        position = fitz.Point(280, 45)
                        page.insert_text(
                            position, 
                            ext_order_no, 
                            fontsize=16, 
                            color=(0, 0, 0)
                        )
                        match_count += 1
            
            if match_count > 0:
                st.success(f"🎯 Done! Successfully Processed Matches: {match_count}/{total_pages}")
                st.download_button(
                    label="📥 Processed PDF Download",
                    data=doc.write(),
                    file_name="Processed_Labels_Final.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ PDF read ho gaya par CSV data se koi match nahi mila. Ek baar columns verify karein.")
        else:
            st.error("❌ CSV headers matched nahi hain. 'Tracking No' aur 'Extern Order No' check karein.")
    except Exception as e:
        st.error(f"Error occurred: {e}")

