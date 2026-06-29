import fitz
from pdf_reader import pdf_to_images
from ocr import read_barcode
import streamlit as st
import os
import pandas as pd

st.set_page_config(
    page_title="Amazon Label Mapper",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Amazon Label Mapper")
st.write("Upload Shipping Label PDF and CSV/Excel")

pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
excel_file = st.file_uploader("Upload CSV / Excel", type=["csv", "xlsx"])

if pdf_file:
    os.makedirs("temp", exist_ok=True)
    pdf_path = os.path.join("temp", pdf_file.name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.read())
    st.success("PDF Uploaded")

if excel_file:
    os.makedirs("temp", exist_ok=True)
    excel_path = os.path.join("temp", excel_file.name)
    with open(excel_path, "wb") as f:
        f.write(excel_file.read())
    st.success("Excel Uploaded")

    if excel_file.name.endswith(".csv"):
        df = pd.read_csv(excel_path)
    else:
        df = pd.read_excel(excel_path)

    st.subheader("Preview")
    st.dataframe(df.head())

if st.button("Process"):
    if pdf_file is None:
        st.error("Upload PDF")
    elif excel_file is None:
        st.error("Upload Excel")
    else:
        # 1. Column headers clean karein
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # 2. Main PDF open karein
        doc = fitz.open(pdf_path)
        images = pdf_to_images(pdf_path)
        match_count = 0
        
        st.info(f"⚡ Processing {len(images)} pages...")
        
        for i, img in enumerate(images):
            awb = read_barcode(img)
            
            if awb:
                awb_clean = str(awb).strip()
                match = df[df["Tracking No_str"] == awb_clean]
                
                if match.empty:
                    match = df[df["Tracking No_str"].str.contains(awb_clean, na=False)]
                
                if not match.empty:
                    extern = str(match.iloc[0]["Extern Order No"])
                    st.write(f"Page {i+1}: Matched -> {extern}")
                    
                    # Sahi page select karein
                    page = doc[i]
                    
                    # --- POSITION LOCK: LEFT SIDE OF AMAZON SHIPPING (BOTTOM) ---
                    # Amazon shipping ke left side wale blank area ka coordinates:
                    # X=30 (Left border alignment), Y=950 (Bottom alignment)
                    position = fitz.Point(30, 950)
                    
                    # Text insert command without any complex formatting
                    page.insert_text(
                        position, 
                        f"{extern}", 
                        fontsize=12, 
                        color=(0, 0, 0)
                    )
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
        
        # 3. PDF KO SAHI SE SAVE & CLOSE KARNA (MAIN STEP)
        if match_count > 0:
            output_pdf_path = os.path.join("temp", f"Processed_{pdf_file.name}")
            
            # Pehle current updates ko write karke document physically close karein
            doc.save(output_pdf_path)
            doc.close()
            
            st.success(f"🎯 Done! Total {match_count} labels updated.")
            
            # Ab save ki hui file ko cleanly read karke download button me dein
            with open(output_pdf_path, "rb") as f:
                processed_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Processed PDF",
                data=processed_bytes,
                file_name=f"Processed_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            doc.close()
            st.error("❌ Kisi bhi label ka match nahi mila.")

