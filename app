import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
import os

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 AWB to External Order PDF Linker")
st.write("PDF Shipping Label aur Excel Sheet upload karein taaki External Order No. automatic insert ho sake.")

# File Uploaders
uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_excel = st.file_uploader("2. Manifest/Data (Excel) Upload Karein", type=["xlsx", "xls"])

if uploaded_pdf and uploaded_excel:
    try:
        # 1. Excel Data Read Karen
        df = pd.read_excel(uploaded_excel)
        
        # Clean Excel Column Names (remove spaces)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Ensure Tracking No and Extern Order No columns exist
        # Tracking No standard format ko handling ke liye string me convert karein
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Read Karen aur AWB Extract Karen
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Pura text extract karein AWB search karne ke liye
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            
            # Regex se AWB Number dhundein (e.g., 168063721758)
            awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', full_text, re.IGNORECASE)
            
            if not awb_match:
                # Agar generic digit pattern check karna ho
                digits = re.findall(r'\b\d{10,15}\b', full_text)
                if digits:
                    awb_number = digits[0]
                else:
                    awb_number = None
            else:
                awb_number = awb_match.group(1)
                
            if awb_number:
                st.info(f"🔍 PDF me **AWB Number** mila: `{awb_number}`")
                
                # 3. Excel me Match Dhundein
                # Scientific notation handling (jaise 1.68064E+11) ke liye broad matching
                matched_row = df[df['Tracking No_str'].str.contains(str(awb_number)[:8], na=False) | (df['Tracking No_str'] == str(awb_number))]
                
                if matched_row.empty and len(str(awb_number)) > 10:
                    # Agar exact match na ho to float mapping try karein
                    try:
                        awb_float = float(awb_number)
                        df['Tracking_float'] = pd.to_numeric(df['Tracking No'], errors='coerce')
                        matched_row = df[df['Tracking_float'] == awb_float]
                    except:
                        pass
                
                if not matched_row.empty:
                    ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                    st.success(f"🎯 Excel me **Extern Order No** mil gaya: `{ext_order_no}`")
                    
                    # 4. PDF me External Order No Paste/Write Karen
                    # Hum pehle page par top ya specific empty box area me likhenge
                    page = doc[0]
                    
                    # Text insert karne ke liye position (X, Y coordinates)
                    # Aap labels ke blank box ke hisab se coordinates adjust kar sakte hain
                    rect = fitz.Rect(20, 520, 300, 540) # Example coordinates jahan red box ho sakta hai
                    
                    # Draw a white rectangle to clear background if needed, then insert text
                    page.insert_text(fitz.Point(30, 535), f"EXT ORDER: {ext_order_no}", fontsize=11, color=(0, 0, 0))
                    
                    # Save PDF to bytes
                    output_pdf_bytes = doc.write()
                    
                    # Download Button
                    st.download_button(
                        label="📥 Processed PDF Download Karein",
                        data=output_pdf_bytes,
                        file_name=f"Processed_{uploaded_pdf.name}",
                        mime="application/pdf"
                    )
                else:
                    st.error(f"❌ AWB `{awb_number}` Excel ke 'Tracking No' column me nahi mila.")
            else:
                st.error("❌ PDF se AWB Number extract nahi kiya ja saka. Kripya check karein ki PDF readable text hai ya scanned image.")
        else:
            st.error("❌ Excel sheet me 'Tracking No' ya 'Extern Order No' naam ka column nahi mila. Kripya check karein.")
            st.write("Mile hue columns:", list(df.columns))
            
    except Exception as e:
        st.error(f"Error occurring: {e}")

