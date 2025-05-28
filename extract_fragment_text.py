import pdfplumber

# Funkcja do ekstrakcji tekstu z konkretnych stron
def extract_pages(pdf_path, start_page, end_page):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(start_page - 1, end_page):
            if i < len(pdf.pages): # Sprawdź, czy strona istnieje
                text += pdf.pages[i].extract_text() + "\n" # Dodaj znak nowej linii po każdej stronie
    return text

# Załóżmy, że artykuł 13 jest na stronie 3
strony_do_ekstrakcji_start = 3
strony_do_ekstrakcji_end = 3

konstytucja_fragment_text = extract_pages("KONSTYTUCJA_RP.pdf", strony_do_ekstrakcji_start, strony_do_ekstrakcji_end)

with open("konstytucja_fragment.txt", "w") as f:
    f.write(konstytucja_fragment_text)
