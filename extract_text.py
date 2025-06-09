import pdfplumber
import PyPDF2
import os

# --- Funkcja do ekstrakcji tekstu za pomocą pdfplumber (preferowana) ---
def extract_pages_pdfplumber(pdf_path, start_page, end_page):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Indeksowanie stron w pdfplumber (i PyPDF2) zaczyna się od 0
            # Więc "strona X" z dokumentu to indeks X-1
            for i in range(start_page - 1, end_page):
                if 0 <= i < len(pdf.pages): # Sprawdź, czy strona istnieje w dokumencie
                    text += pdf.pages[i].extract_text() + "\n" # Dodaj znak nowej linii po każdej stronie
        return text
    except Exception as e:
        print(f"Błąd pdfplumber podczas przetwarzania pliku '{pdf_path}': {e}")
        print("Spróbuj użyć alternatywnej metody (PyPDF2) lub sprawdź plik PDF.")
        return None # Zwróć None w przypadku błędu

# --- Alternatywna funkcja do ekstrakcji tekstu za pomocą PyPDF2 ---
# Użyj tej funkcji, jeśli pdfplumber napotka błędy (np. "No /Root object!")
def extract_pages_pypdf2(pdf_path, start_page, end_page):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for i in range(start_page - 1, end_page):
                if 0 <= i < len(reader.pages):
                    page_obj = reader.pages[i]
                    text += page_obj.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Błąd PyPDF2 podczas przetwarzania pliku '{pdf_path}': {e}")
        print("Upewnij się, że plik PDF nie jest uszkodzony lub zabezpieczony.")
        return None

# --- Konfiguracja ścieżek i stron ---
# Upewnij się, że ten plik PDF znajduje się w tym samym katalogu co skrypt Python
pdf_file_name = "Gmail_True_Justice.pdf" # Zmieniona nazwa pliku bez "&"
output_txt_file = "gmail_justice_fragment.txt"

# Zakres stron do ekstrakcji
# Pamiętaj, że to są numery stron z dokumentu, nie indeksy programistyczne
start_page_num = 58
end_page_num = 88

# --- Główna logika skryptu ---
print(f"Próba ekstrakcji tekstu ze stron od {start_page_num} do {end_page_num} z pliku: {pdf_file_name}")

# Sprawdź, czy plik PDF istnieje
if not os.path.exists(pdf_file_name):
    print(f"Błąd: Plik PDF '{pdf_file_name}' nie został znaleziony w katalogu '{os.getcwd()}'")
    print("Upewnij się, że plik został zmieniony i przeniesiony do tego katalogu.")
else:
    extracted_text = extract_pages_pdfplumber(pdf_file_name, start_page_num, end_page_num)

    # Jeśli pdfplumber zawiódł, spróbuj PyPDF2
    if extracted_text is None:
        print("\nPróba użycia PyPDF2 jako alternatywy...")
        extracted_text = extract_pages_pypdf2(pdf_file_name, start_page_num, end_page_num)

    if extracted_text:
        try:
            with open(output_txt_file, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            print(f"\nTekst ze stron {start_page_num}-{end_page_num} został pomyślnie zapisany do pliku: {output_txt_file}")
        except Exception as e:
            print(f"Błąd podczas zapisu pliku tekstowego: {e}")
    else:
        print("Nie udało się wyodrębnić tekstu z PDF za pomocą żadnej z metod.")