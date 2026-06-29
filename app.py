import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="AWB to External Order Linker", layout="centered")
st.title("📦 Perfect AWB Matcher (Debug Enabled)")
st.write("Multi-page PDF aur Manifest (CSV) upload karein.")

uploaded_pdf = st.file_uploader("1. Shipping Label (PDF) Upload Karein", type=["pdf"])
uploaded_csv = st.file_uploader("2. Manifest Data (CSV) Upload Karein", type=["csv"])

if uploaded_pdf and uploaded_csv:
    try:
        # 1. CSV Read Karen aur complete clean karein
        df = pd.read_csv(uploaded_csv)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            # Clean CSV Tracking Numbers: Remove spaces, decimals (.0), and convert to clean string
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PDF Open Karen
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            
            st.info(f"⚡ Total {total_pages} pages analyze ho rhe hain...")
            
            match_count = 0
            debug_info = [] # Logs collect karne ke liye
            
            # Har page par fast text search loop
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Pure text ko aasan tarike se extract karein
                page_text = page.get_text("text")
                
                # --- Advanced AWB Extraction Logic ---
                # Sare continuous numbers nikalo jo 10 se 15 digit ke hon (spaces aur newlines remove karke)
                clean_text_for_digits = re.sub(r'\s+', '', page_text)
                digits_found = re.findall(r'\d{10,15}', clean_text_for_digits)
                
                # AWB pattern specific check
                awb_match = re.search(r'AWB\s*[:\-\s]*(\d+)', page_text, re.IGNORECASE)
                
                awb_number = None
                if awb_match:
                    awb_number = awb_match.group(1).strip()
                elif digits_found:
                    # Amazon AWB standard format ke hisab se 11-15 digit ka pehla valid number
                    for d in digits_found:
                        if len(d) >= 11:
                            awb_number = d
                            break
                    if not awb_number:
                        awb_number = digits_found[0]
                
                if awb_number:
                    # CSV me strict aur partial dono match check karein
                    awb_clean = str(awb_number).strip()
                    
                    # Try 1: Exact Match
                    matched_row = df[df['Tracking No_str'] == awb_clean]
                    
                    # Try 2: Partial Match (Contains)
                    if matched_row.empty:
                        matched_row = df[df['Tracking No_str'].str.contains(awb_clean, na=False) | df['Tracking No_str'].apply(lambda x: awb_clean in str(x))]
                    
                    if not matched_row.empty:
                        ext_order_no = str(matched_row.iloc[0]['Extern Order No'])
                        
                        # Amazon Shipping ke right me stamp karein: X=280, Y=45
                        position = fitz.Point(280, 45)
                        page.insert_text(
                            position, 
                            ext_order_no, 
                            fontsize=14, 
                            fontname="helv-bold", 
                            color=(0, 0, 0)
                        )
                        match_count += 1
                        if page_num < 5: # Sirf pehle 5 ka debug data store karein taaki screen na bhare
                            debug_info.append(f"✅ Page {page_num+1}: AWB `{awb_clean}` Matched with Order `{ext_order_no}`")
                    else:
                        if page_num < 5:
                            debug_info.append(f"❌ Page {page_num+1}: AWB `{awb_clean}` extracted, but NOT found in CSV.")
                else:
                    if page_num < 5:
                        debug_info.append(f"⚠️ Page {page_num+1}: PDF se koi AWB Number read nahi ho paya.")
            
            # --- DEBUG SHOW WINDOW ---
            st.subheader("🔍 Debugging Logs (Pehle 5 Pages Ka Report)")
            for log in debug_info:
                st.write(log)
                
            if match_count > 0:
                st.success(f"🎯 Successful Matches: {match_count}/{total_pages}")
                output_pdf_bytes = doc.write()
                st.download_button(
                    label="📥 Processed PDF Download Karein",
                    data=output_pdf_bytes,
                    file_name=f"Processed_Labels.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Kisi bhi page ka AWB CSV se match nahi ho paya.")
                # CSV ke shuruati sample numbers dikhayein taaki matching check ho sake
                st.write("📋 Aapke CSV me 'Tracking No' ke shuruati 5 records ye hain:")
                st.write(df['Tracking No_str'].head().tolist())
                
        else:
            st.error("❌ CSV headers galat hain. Make sure columns are 'Tracking No' and 'Extern Order No'")
            
    except Exception as e:
        st.error(f"Error occurred: {e}")

