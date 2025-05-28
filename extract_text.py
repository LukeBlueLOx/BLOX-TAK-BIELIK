import pdfplumber

with pdfplumber.open("KONSTYTUCJA_RP.pdf") as pdf:
    konstytucja_text = "".join(page.extract_text() for page in pdf.pages)

with open("konstytucja.txt", "w") as f:
    f.write(konstytucja_text)