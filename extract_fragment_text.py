import pdfplumber

# Funkcja do ekstrakcji tekstu z konkretnych stron
def extract_pages(pdf_path, start_page, end_page):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        # Pamiętaj, że w Pythonie indeksowanie zaczyna się od 0
        # Więc strona 3 to indeks 2
        for i in range(start_page - 1, end_page):
            if i < len(pdf.pages): # Sprawdź, czy strona istnieje
                text += pdf.pages[i].extract_text() + "\n" # Dodaj znak nowej linii po każdej stronie
    return text

# Załóżmy, że artykuł 13 jest na stronie 3
# Możesz podać zakres np. od strony 2 do 4, żeby dać modelowi trochę więcej kontekstu
strony_do_ekstrakcji_start = 2 # Strona 2 PDF to indeks 1
strony_do_ekstrakcji_end = 4   # Strona 4 PDF to indeks 3

konstytucja_fragment_text = extract_pages("KONSTYTUCJA_RP.pdf", strony_do_ekstrakcji_start, strony_do_ekstrakcji_end)

with open("konstytucja_fragment.txt", "w") as f:
    f.write(konstytucja_fragment_text)

# Jeśli nadal potrzebujesz całego sprzeciwu:
with pdfplumber.open("SPRZECIW_2025-03-03.pdf") as pdf:
    sprzeciw_text = "".join(page.extract_text() for page in pdf.pages)
with open("sprzeciw.txt", "w") as f:
    f.write(sprzeciw_text)