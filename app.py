import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Final Fixed AWB Matcher")

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
                
                # Alternately check for Invoice ID/Order ID format (e.g., M07-2627-06697)
                invoice_match = re.search(r'INVOICE\s*ID\s*[:\-\s]*([A-Z0-9\-]+)', page_text, re.IGNORECASE)
                
                if awb_number:
                    awb_clean = str(awb_number).strip()
                    matched_row = df[df['Tracking No_clean'] == awb_clean]
                    
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_clean'].str.contains(awb_clean, na=False)]
                        
                    # Target Try with Invoice ID fallback if mapping exists
                    if matched_row.empty and invoice_match:
                        inv_clean = invoice_match.group(1).strip()
                        if 'Order No' in df.columns:
                            matched_row = df[df['Order No'].astype(str).str.contains(inv_clean, na=False)]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # --- ATTRIBUTE ERROR PERMANENT FIX ---
                        # PyMuPDF ke naye versions me 'insert_text' ki jagah 'insert_textbox' ya 'page.insert_text' ko clear method mila h
                        # Agar direct method fail ho toh hum safety point injection standard format follow karte hain
                        try:
                            page.insert_text(fitz.Point(280, 45), ext_order_no, fontsize=16, fontname="helv", color=(0, 0, 0))
                        except AttributeError:
                            # Naye version fallback wrapper
                            rect = fitz.Rect(280, 30, 500, 60)
                            page.insert_textbox(rect, ext_order_no, fontsize=16, fontname="helv", color=(0, 0, 0))
                            
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
            st.error("❌ CSV columns check karein ('Tracking No' aur 'Extern Order No').")
    except Exception as e:
        st.error(f"Error occurred: {e}")

