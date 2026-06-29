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

pdf_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

excel_file = st.file_uploader(
    "Upload CSV / Excel",
    type=["csv", "xlsx"]
)

if pdf_file:

    os.makedirs("temp", exist_ok=True)

    pdf_path = os.path.join(
        "temp",
        pdf_file.name
    )

    with open(pdf_path, "wb") as f:
        f.write(pdf_file.read())

    st.success("PDF Uploaded")

if excel_file:

    os.makedirs("temp", exist_ok=True)

    excel_path = os.path.join(
        "temp",
        excel_file.name
    )

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
        images = pdf_to_images(pdf_path)

        for i, img in enumerate(images):

    awb = read_barcode(img)

    match = df[df["Tracking No"].astype(str) == str(awb)]

    if not match.empty:
        extern = match.iloc[0]["Extern Order No"]
        st.write(f"Page {i+1}: {extern}")
    else:
        st.write(f"Page {i+1}: NOT FOUND")
