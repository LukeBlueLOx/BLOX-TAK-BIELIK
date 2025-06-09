import os
import pdfplumber
import json
import http.client  # For making HTTP requests
import textwrap
import datetime

# --- Konfiguracja ścieżek ---
PDF_INPUT_FOLDER = "/home/luke_blue_lox/PycharmProjects/BLOX-TAK-BIELIK/FOR_ANALYSIS"
OUTPUT_FOLDER = "/home/luke_blue_lox/PycharmProjects/BLOX-TAK-BIELIK/PROCESSED_OUTPUT_BIELIK"  # Zmieniona ścieżka wyjściowa
LOG_FOLDER = ("/home/luke_blue_lox/PycharmProjects/BLOX-TAK-BIELIK/2"
              "2")  # Zmieniona ścieżka logów

# Aktualny czas
now = datetime.datetime.now()

# Format ISO 8601 z milisekundami
full_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.%f%z")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# --- Konfiguracja Ollama API dla BIELIKA ---
OLLAMA_HOST = "localhost"  # lub adres IP, jeśli Ollama/BIELIK działa na innej maszynie
OLLAMA_PORT = 11434
MODEL_NAME = "bielik-4.5b-q4km-final"  # Upewnij się, że to poprawna nazwa modelu w Ollama

# Rozmiary chunków - mogą wymagać dostosowania w zależności od możliwości BIELIKA i pamięci
CHUNK_SIZE = 100_000  # Rozmiar chunka dla pojedynczych dokumentów (w znakach)
OVERALL_SUMMARY_CHUNK_SIZE = 50_000  # Rozmiar chunka dla globalnego podsumowania (w znakach)


# --- Funkcja do ekstrakcji CAŁEGO tekstu ---
def extract_text_from_pdf_full(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"BŁĄD: Nie można wyodrębnić tekstu z {pdf_path}: {e}")
        return None
    return text.strip()


# --- Funkcja do ekstrakcji tekstu z WYBRANYCH STRON ---
def extract_selected_pages_from_pdf(pdf_path, start_page, end_page):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)

            actual_start_index = max(0, start_page - 1)
            actual_end_index = min(num_pages, end_page)

            if actual_start_index >= num_pages:
                print(
                    f"OSTRZEŻENIE: Strona początkowa {start_page} wykracza poza liczbę stron PDF ({num_pages}). Zwracam pusty tekst.")
                return ""
            if actual_start_index >= actual_end_index:
                print(
                    f"OSTRZEŻENIE: Zakres stron ({start_page}-{end_page}) jest nieprawidłowy lub pusty. Zwracam pusty tekst.")
                return ""

            print(
                f"Ekstrakcja stron od {actual_start_index + 1} do {actual_end_index} z pliku '{os.path.basename(pdf_path)}'...")

            for i in range(actual_start_index, actual_end_index):
                page = pdf.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    print(f"  INFO: Strona {i + 1} jest pusta lub nie zawiera tekstu.")
    except Exception as e:
        print(f"BŁĄD: Nie można wyodrębnić tekstu z {pdf_path} dla stron {start_page}-{end_page}: {e}")
        return None
    return text.strip()


# --- Funkcja do interaktywnego pobierania zakresu stron ---
def get_page_range_input(pdf_file_name, total_pages):
    while True:
        choice = input(f"Dla pliku '{pdf_file_name}' (łącznie stron: {total_pages}):\n"
                       f"1. Przetwórz wszystkie strony\n"
                       f"2. Podaj zakres stron (np. 10-20)\n"
                       f"Wybierz opcję (1/2): ").strip()

        if choice == '1':
            return 1, total_pages
        elif choice == '2':
            page_range_str = input("Podaj zakres stron (np. 10-20): ").strip()
            try:
                start_str, end_str = page_range_str.split('-')
                start_page = int(start_str)
                end_page = int(end_str)
                if 1 <= start_page <= end_page <= total_pages:
                    return start_page, end_page
                else:
                    print(
                        f"BŁĄD: Nieprawidłowy zakres stron. Upewnij się, że {1} <= początek <= koniec <= {total_pages}.")
            except ValueError:
                print("BŁĄD: Nieprawidłowy format. Użyj formatu 'START-KONIEC', np. '10-20'.")
        else:
            print("Nieprawidłowy wybór. Proszę wybrać 1 lub 2.")


def analyze_text_with_bielik(text_to_analyze, prompt_prefix=""):
    """
    Analizuje tekst używając modelu BIELIK poprzez Ollama API.
    """
    if not text_to_analyze.strip():
        print("INFO: Brak tekstu do analizy dla BIELIKA. Zwracam pusty string.")
        return ""

    # Dzielenie tekstu na chunki na podstawie liczby znaków
    # textwrap.wrap dzieli tekst na listę stringów, każdy o maksymalnej długości CHUNK_SIZE
    chunks = textwrap.wrap(text_to_analyze, CHUNK_SIZE, break_long_words=False, replace_whitespace=False,
                           drop_whitespace=False)

    if not chunks:
        print("OSTRZEŻENIE: Tekst nie został podzielony na chunki prawidłowo. Zwracam pusty string.")
        return ""

    full_analysis = []
    print(f"Tekst zostanie podzielony na {len(chunks)} części do analizy przez BIELIKA.")

    for i, chunk in enumerate(chunks):
        print(f"Analizuję część {i + 1}/{len(chunks)} ({len(chunk)} znaków) z BIELIKIEM...")

        # Prompt dla BIELIKA - dostosowany do analizy prawnej
        base_prompt = (
                f"Jesteś wysoce doświadczonym ekspertem prawnym, specjalizującym się w prawie cywilnym, egzekucyjnym i socjalnym w Polsce. "
                f"Przeanalizuj dokument pod kątem Prawa Polskiego i Unii Europejskiej, zidentyfikuj kluczowe fakty prawne, terminy, strony, roszczenia, zobowiązania, dowody oraz oświadczenia dotyczące sytuacji finansowej i zdrowotnej Łukasza Andruszkiewicza. "
                f"Szczególną uwagę zwróć na: odniesienia do sytuacji finansowej, długów, dochodów, zatrudnienia, prób znalezienia pracy; szczegóły stanu zdrowia, wypadków, urazów, braku ubezpieczenia; wzmianki o próbach uzyskania pomocy od instytucji; konieczność podjęcia pracy zdalnej; oświadczenia dotyczące braku majątku i trudności egzystencji; adresatów, daty i sygnatury akt. Zacytuj odpowiednie artykuły i opisz jakie prawa zostały złamane. "
                f"Wynik podaj w języku Polskim i Angielskim. Podaj również na końcu treść użytego promptu - analogicznie w języku "
                f"Polskim i Angielskim, a także wersję modelu jaki został użyty - czyli: Bielik-4.5B-v3.0-Instruct-Q4_K_M.gguf,"
                f"z pełnym timestamp: " + full_timestamp
        )
        # Łączenie promptu prefix (jeśli istnieje) z bazowym promptem i tekstem do analizy
        prompt_content = f"{prompt_prefix}\n\n{base_prompt}\n\nTekst do analizy:\n\n{chunk}"

        messages_payload = [
            {'role': 'user', 'content': prompt_content}
        ]

        request_body = json.dumps({
            "model": MODEL_NAME,
            "messages": messages_payload,
            "stream": False,
            # Można dodać opcje, jeśli BIELIK/Ollama je wspiera, np.:
            # "options": {
            #     "temperature": 0.2,
            #     "top_p": 0.9,
            #     "top_k": 30
            # }
        })

        chunk_analysis_part = ""
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=None)  # Timeout 5 minut
            headers = {'Content-Type': 'application/json'}

            print(f"  Wysyłanie zapytania do BIELIK API (Ollama) dla części {i + 1}...")
            conn.request("POST", "/api/chat", body=request_body, headers=headers)
            response = conn.getresponse()
            response_data_raw = response.read()
            response_data_decoded = response_data_raw.decode('utf-8')
            conn.close()

            print(f"  Status odpowiedzi BIELIK API dla części {i + 1}: {response.status}")

            if response.status == 200:
                result = json.loads(response_data_decoded)
                if 'message' in result and 'content' in result['message']:
                    chunk_analysis_part = result['message']['content'].strip()
                    full_analysis.append(chunk_analysis_part)
                    print(
                        f"  Otrzymano analizę od BIELIKA dla części {i + 1} (fragment): {chunk_analysis_part[:100]}...")
                else:
                    print(
                        f"  OSTRZEŻENIE: BIELIK nie zwrócił oczekiwanej treści w 'message.content' dla części {i + 1}.")
                    print(f"  Pełna odpowiedź BIELIKA: {response_data_decoded}")
                    full_analysis.append(
                        f"[BRAK ANALIZY OD BIELIKA DLA TEJ CZĘŚCI - NIEPRAWIDŁOWY FORMAT ODPOWIEDZI]\n{response_data_decoded}\n")
            else:
                print(f"  BŁĄD: Serwer BIELIK (Ollama) zwrócił błąd HTTP {response.status} dla części {i + 1}.")
                print(f"  Odpowiedź serwera: {response_data_decoded}")
                full_analysis.append(
                    f"[BŁĄD SERWERA BIELIK ({response.status}) DLA TEJ CZĘŚCI]\n{response_data_decoded}\n")

        except http.client.RemoteDisconnected as e:
            print(
                f"KRYTYCZNY BŁĄD: Połączenie z serwerem BIELIK (Ollama) zostało nieoczekiwanie zamknięte dla części {i + 1}: {e}")
            full_analysis.append(f"[BŁĄD POŁĄCZENIA Z BIELIKIEM (RemoteDisconnected) DLA TEJ CZĘŚCI: {e}]\n")
        except ConnectionRefusedError as e:
            print(
                f"KRYTYCZNY BŁĄD: Nie można połączyć się z serwerem BIELIK (Ollama) - {OLLAMA_HOST}:{OLLAMA_PORT}. Upewnij się, że serwer działa. Błąd: {e}")
            full_analysis.append(f"[BŁĄD POŁĄCZENIA Z BIELIKIEM (ConnectionRefused) DLA TEJ CZĘŚCI: {e}]\n")
            # Można tu dodać `return ""` jeśli chcemy przerwać całą analizę pliku przy braku połączenia
        except Exception as e:
            print(f"KRYTYCZNY BŁĄD: Podczas komunikacji z BIELIK API (Ollama) dla części {i + 1}: {e}")
            print(f"  Typ błędu: {type(e).__name__}")
            full_analysis.append(f"[BŁĄD ANALIZY BIELIK DLA TEJ CZĘŚCI: {e}]\n")
            if 'response_data_decoded' in locals():  # Jeśli zdążyło pobrać odpowiedź
                print(f"  Surowa odpowiedź (jeśli dostępna): {response_data_decoded}")

    final_analysis = "\n\n---\n\n".join(full_analysis)
    return final_analysis


def summarize_overall_legal_findings_with_bielik(all_summaries_text):
    """
    Generuje globalne podsumowanie prawne używając modelu BIELIK.
    """
    print("\n\n--- Generowanie globalnego podsumowania prawnego z BIELIKIEM ---")
    if not all_summaries_text.strip():
        print("Brak danych do globalnego podsumowania dla BIELIKA. Zwracam pusty tekst.")
        return ""

    overall_chunks = textwrap.wrap(all_summaries_text, OVERALL_SUMMARY_CHUNK_SIZE, break_long_words=False,
                                   replace_whitespace=False, drop_whitespace=False)

    overall_summary_parts = []

    base_overall_prompt = (
        f"Jesteś wysoce doświadczonym ekspertem prawnym, specjalizującym się w prawie cywilnym, egzekucyjnym i socjalnym w Polsce. "
        f"Twoim zadaniem jest przygotowanie kompleksowych i rzeczowych wyjaśnień dla Kancelarii Komorniczych, "
        f"bazując na całości dostarczonego dokumentu (połączonego z wielu źródeł). "
        f"Celem jest przedstawienie aktualnej, bardzo trudnej sytuacji finansowej, zdrowotnej i życiowej dłużnika Łukasza Andruszkiewicza, "
        f"zgodnie z wezwaniem od Komornika Joanny Majdak (odwołując się do treści dokumentu). "
        f"W swoich wyjaśnieniach, uwzględnij i szczegółowo opisz następujące punkty, odwołując się do treści dokumentu i przekazanych informacji:"
        f"\n\n1.  **Potwierdzenie aktualnej trudnej sytuacji:** Jasno zaznacz, że sytuacja dłużnika nie uległa poprawie od poprzednich wyjaśnień i jest bardzo trudna (odwołaj się do dokumentów np. 'SPRZECIW_Nc-e_1932318_24_2025-04-27.pdf' oraz 'Gmail - Wyjaśnienia 2024-08-12.PDF', wskazując na pogorszenie i brak możliwości spłaty). "
        f"\n\n2.  **Szczegółowy opis stanu zdrowia i jego wpływu na sytuację:** "
        f"    Wspomnij o wypadku z 1 maja, nieleczonych urazach (oczodół, policzek, zęby, staw skroniowo-żuchwowy, kolano, ścięgno Achillesa), braku ubezpieczenia zdrowotnego i niemożności odbycia badań kontrolnych (odwołaj się do 'Gmail - KM 1623_22.pdf' oraz 'Cover Letter.pdf'). "
        f"    Podkreśl zagrożenie neuralgią nerwu trójdzielnego jako konsekwencję urazów ('SPRZECIW_Nc-e_1932318_24_2025-04-27.pdf'). "
        f"    Wspomnij o braku wsparcia instytucjonalnego w kwestii zdrowia i ubezpieczenia (np. odmowa PUP). "
        f"\n\n3.  **Opis sytuacji finansowej i majątkowej:** "
        f"    Zadeklaruj brak możliwości spłaty zadłużenia. "
        f"    Jasno określ, że jedyną rzeczą, jaką udało się nabyć, są przedmioty z faktury 'F_2025_19384_1.pdf' (adapter dysku NVME M.2, Raspberry Pi 256GB SSD, koszt dostawy), podając ich wartość. "
        f"    Wyjaśnij pochodzenie środków na ten zakup: ostatnie odłożone pieniądze od zeszłego roku, w tym 100 PLN od Brata na święta i 100 PLN od rodziców za rozliczenie zeznań podatkowych w bieżącym roku. "
        f"    Podkreśl, że był to **konieczny wydatek** w celu dokończenia portfolio związanego z ekosystemem TAK, co jest kluczowe dla prób zarobienia pieniędzy. "
        f"    Wspomnij o aktywnych, lecz dotychczas bezskutecznych próbach znalezienia zatrudnienia/współpracy, co prowadzi do braku dochodów. "
        f"    Potwierdź, że dłużnik nie posiada innych znaczących środków ani majątku poza wymienionymi. "
        f"    Odwołaj się do wszelkich wcześniejszych oświadczeń o trudnej sytuacji finansowej, wyzysku, braku wsparcia od Państwa Polskiego i UE, oraz żądaniach odszkodowań (np. w 'SPRZECIW_2025-03-03.pdf', 'ODWOŁANIE-SeriaP_Nr0360-2025-01-13_GOV-PL_2025-01-30'). "
        f"\n\n4.  **Konsekwencje i oczekiwania dłużnika:** "
        f"    Wspomnij o konieczności prowadzenia korespondencji z zagranicy i braku odpowiedzi. "
        f"    Zaznacz, że dłużnik żąda prawnika, którego wynagrodzenie pokryje Fundusz Sprawiedliwości, oraz renty czasowej z ubezpieczeniem zdrowotnym, aby mógł zadbać o swoje zdrowie i przeprowadzić upadłość. ('SPRZECIW_2025-03-03.pdf') "
        f"    Podkreśl, że dłużnik nie jest w stanie obecnie stawiać się przed instytucjami w regionie (Dolny Śląsk) ze względu na doświadczenia (odwołaj się do 'Pismo Właściwe.pdf' oraz 'SPRZECIW_2025-03-03.pdf')."
        f"\n\nZadbaj o to, aby wyjaśnienia były kompleksowe, spójne, rzeczowe i empatyczne, jednocześnie ściśle trzymając się faktów zawartych w dokumentacji. Tekst wygenerowany przez model będzie stanowił trzon pisma do kancelarii komorniczej."
    )

    for i, chunk in enumerate(overall_chunks):
        print(
            f"Analizuję część {i + 1}/{len(overall_chunks)} globalnego podsumowania z BIELIKIEM ({len(chunk)} znaków)...")
        prompt_content = f"{base_overall_prompt}\n\nAnalizy do podsumowania:\n\n{chunk}"

        messages_payload = [{'role': 'user', 'content': prompt_content}]
        request_body = json.dumps({
            "model": MODEL_NAME,
            "messages": messages_payload,
            "stream": False
        })

        current_summary_part = ""
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=None)  # Timeout 5 minut
            headers = {'Content-Type': 'application/json'}

            print(f"  Wysyłanie zapytania do BIELIK API (Ollama) dla globalnego podsumowania, część {i + 1}...")
            conn.request("POST", "/api/chat", body=request_body, headers=headers)
            response = conn.getresponse()
            response_data_raw = response.read()
            response_data_decoded = response_data_raw.decode('utf-8')
            conn.close()

            print(f"  Status odpowiedzi BIELIK API dla globalnego podsumowania, część {i + 1}: {response.status}")

            if response.status == 200:
                result = json.loads(response_data_decoded)
                if 'message' in result and 'content' in result['message']:
                    current_summary_part = result['message']['content'].strip()
                    overall_summary_parts.append(current_summary_part)
                    print(f"  Otrzymano fragment globalnego podsumowania od BIELIKA (część {i + 1}).")
                else:
                    print(
                        f"  OSTRZEŻENIE: BIELIK nie zwrócił oczekiwanej treści dla globalnego podsumowania (część {i + 1}).")
                    print(f"  Pełna odpowiedź BIELIKA: {response_data_decoded}")
                    overall_summary_parts.append(
                        f"[BRAK PODSUMOWANIA OD BIELIKA DLA TEJ CZĘŚCI - BŁĄD FORMATU]\n{response_data_decoded}\n")
            else:
                print(
                    f"  BŁĄD: Serwer BIELIK (Ollama) zwrócił błąd HTTP {response.status} dla globalnego podsumowania (część {i + 1}).")
                print(f"  Odpowiedź serwera: {response_data_decoded}")
                overall_summary_parts.append(
                    f"[BŁĄD SERWERA BIELIK ({response.status}) DLA GLOBALNEGO PODSUMOWANIA, CZĘŚĆ {i + 1}]\n{response_data_decoded}\n")

        except http.client.RemoteDisconnected as e:
            print(
                f"KRYTYCZNY BŁĄD: Połączenie z serwerem BIELIK (Ollama) zostało nieoczekiwanie zamknięte dla globalnego podsumowania, część {i + 1}: {e}")
            overall_summary_parts.append(
                f"[BŁĄD POŁĄCZENIA Z BIELIKIEM (RemoteDisconnected) DLA GLOBALNEGO PODSUMOWANIA, CZĘŚĆ {i + 1}: {e}]\n")
        except ConnectionRefusedError as e:
            print(
                f"KRYTYCZNY BŁĄD: Nie można połączyć się z serwerem BIELIK (Ollama) dla globalnego podsumowania - {OLLAMA_HOST}:{OLLAMA_PORT}. Błąd: {e}")
            overall_summary_parts.append(
                f"[BŁĄD POŁĄCZENIA Z BIELIKIEM (ConnectionRefused) DLA GLOBALNEGO PODSUMOWANIA, CZĘŚĆ {i + 1}: {e}]\n")
        except Exception as e:
            print(f"KRYTYCZNY BŁĄD: Podczas komunikacji z BIELIK API dla globalnego podsumowania (część {i + 1}): {e}")
            overall_summary_parts.append(f"[GLOBALNE PODSUMOWANIE BIELIK: BŁĄD ANALIZY DLA TEJ CZĘŚCI: {e}]\n")
            if 'response_data_decoded' in locals():
                print(f"  Surowa odpowiedź (jeśli dostępna): {response_data_decoded}")

    final_overall_summary = "\n\n".join(overall_summary_parts)
    return final_overall_summary


def write_usage_summary(total_files, total_duration):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(LOG_FOLDER, f"bielik_usage_summary_{timestamp}.txt")

    # Uproszczone podsumowanie, bez tokenów, bo Ollama API ich nie zwraca standardowo
    summary_content = (
        f"--- Podsumowanie Uruchomienia BLOX-TAK-BIELIK ---\n"
        f"Data i czas uruchomienia: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Przetworzone plików PDF: {total_files}\n"
        f"Użyty model BIELIK (przez Ollama): {MODEL_NAME} na {OLLAMA_HOST}:{OLLAMA_PORT}\n"
        f"Łączny czas przetwarzania: {total_duration:.2f} sekund\n"
        f"--------------------------------------------------\n"
        f"UWAGA: Zliczanie tokenów nie jest wspierane bezpośrednio przez to API Ollama. "
        f"Sprawdź logi konsoli powyżej dla szczegółów odpowiedzi od BIELIKA.\n"
    )

    try:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
        print(f"\n--- Podsumowanie użycia (BIELIK) zapisano do: {log_file_path} ---")
    except Exception as e:
        print(f"BŁĄD: Nie można zapisać pliku podsumowania zużycia (BIELIK): {e}")


def process_all_pdfs_with_bielik():
    print(f"Rozpoczynam analizę plików PDF z folderu: {PDF_INPUT_FOLDER} używając BIELIKA")

    pdf_files = [f for f in os.listdir(PDF_INPUT_FOLDER) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("INFO: Brak plików PDF w folderze do analizy.")
        return

    processed_files_count = 0
    legal_summaries = []
    all_individual_analyses_text = []

    start_time_script = datetime.datetime.now()

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_INPUT_FOLDER, pdf_file)
        base_name = os.path.splitext(pdf_file)[0]
        # Zmieniona nazwa pliku wyjściowego, aby odróżnić od wyników Gemini
        output_txt_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_bielik_analysis.txt")

        print(f"\n--- Przetwarzanie pliku (BIELIK): {pdf_file} ---")

        num_pages = 0
        try:
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
        except Exception as e:
            print(
                f"BŁĄD: Nie można otworzyć pliku PDF '{pdf_file}' w celu sprawdzenia liczby stron: {e}. Pomijam plik.")
            continue

        start_p, end_p = get_page_range_input(pdf_file, num_pages)
        extracted_text = extract_selected_pages_from_pdf(pdf_path, start_p, end_p)

        if extracted_text is None:
            print(f"BŁĄD: Pomijam plik '{pdf_file}' z powodu problemów z ekstrakcją tekstu.")
            summary_content = f"--- Analiza BIELIK dla pliku: {pdf_file} ---\n[BŁĄD EKSTRAKCJI TEKSTU Z PDF]\n"
            try:
                with open(output_txt_path, "w", encoding="utf-8") as f:
                    f.write("[BŁĄD EKSTRAKCJI TEKSTU Z PDF]")
            except Exception as e_write:
                print(f"BŁĄD zapisu informacji o błędzie ekstrakcji dla {pdf_file}: {e_write}")
            legal_summaries.append(summary_content)
            all_individual_analyses_text.append(summary_content)
            continue

        if not extracted_text.strip():  # Sprawdzamy czy tekst nie jest pusty po usunięciu białych znaków
            print(
                f"INFO: Plik '{pdf_file}' jest pusty lub nie zawiera tekstu po ekstrakcji dla wybranego zakresu. Pomijam analizę BIELIKIEM.")
            summary_content = f"--- Analiza BIELIK dla pliku: {pdf_file} ---\n[PLIK PUSTY LUB BEZ TEKSTU DO ANALIZY]\n"
            try:
                with open(output_txt_path, "w", encoding="utf-8") as f:
                    f.write("[PLIK PUSTY LUB BEZ TEKSTU DO ANALIZY]")
            except Exception as e_write:
                print(f"BŁĄD zapisu informacji o pustym pliku dla {pdf_file}: {e_write}")
            legal_summaries.append(summary_content)
            all_individual_analyses_text.append(summary_content)
            continue

        # Analiza z BIELIKIEM
        legal_analysis_result = analyze_text_with_bielik(extracted_text)
        processed_files_count += 1

        if legal_analysis_result is not None and legal_analysis_result.strip():
            try:
                with open(output_txt_path, "w", encoding="utf-8") as f:
                    f.write(legal_analysis_result)
                print(f"SUKCES (BIELIK): Wynik analizy prawnej zapisano do: {output_txt_path}")
                summary_content_for_list = f"--- Analiza BIELIK dla pliku: {pdf_file} ---\n" + legal_analysis_result + "\n"
            except Exception as e:
                print(f"BŁĄD (BIELIK): Nie można zapisać wyniku analizy dla {pdf_file}: {e}")
                summary_content_for_list = f"--- Analiza BIELIK dla pliku: {pdf_file} ---\n[BŁĄD ZAPISU WYNIKU ANALIZY BIELIK: {e}]\n"
        else:
            print(
                f"OSTRZEŻENIE (BIELIK): Nie uzyskano sensownego wyniku analizy dla '{pdf_file}'. Sprawdź logi.")
            summary_content_for_list = f"--- Analiza BIELIK dla pliku: {pdf_file} ---\n[NIE UZYSKANO WYNIKU ANALIZY Z BIELIKA LUB WYNIK PUSTY]\n"
            try:
                with open(output_txt_path, "w", encoding="utf-8") as f:  # Zapisz informację o braku wyniku
                    f.write("[NIE UZYSKANO WYNIKU ANALIZY Z BIELIKA LUB WYNIK PUSTY]")
            except Exception as e_write:
                print(f"BŁĄD zapisu informacji o braku wyniku dla {pdf_file}: {e_write}")

        legal_summaries.append(summary_content_for_list)
        # Dodajemy tylko faktyczną analizę, jeśli istnieje, do globalnego podsumowania
        if legal_analysis_result and "[BŁĄD" not in legal_analysis_result and "[BRAK ANALIZY" not in legal_analysis_result:
            all_individual_analyses_text.append(legal_analysis_result)
        else:  # Jeśli był błąd lub brak analizy, dodajemy notatkę
            all_individual_analyses_text.append(
                f"[PROBLEM Z ANALIZĄ PLIKU {pdf_file} - POMINIĘTO W GLOBALNYM PODSUMOWANIU]\n{legal_analysis_result if legal_analysis_result else ''}")

        print(f"--- Zakończono przetwarzanie pliku '{pdf_file}' z BIELIKIEM ---")
        print("-------------------------------------------------")

    end_time_script = datetime.datetime.now()
    total_processing_duration = (end_time_script - start_time_script).total_seconds()

    print("\n--- Zakończono przetwarzanie wszystkich plików PDF z BIELIKIEM. ---")

    print("\n\n--- ZBIORCZE PODSUMOWANIE PRAWNE (BIELIK) DLA KAŻDEGO DOKUMENTU ---")
    for summary in legal_summaries:
        print(summary)
    print("----------------------------------------------------------\n")

    combined_analyses_for_overall_summary = "\n\n".join(
        filter(None, all_individual_analyses_text))  # Filtruj puste wpisy

    if combined_analyses_for_overall_summary.strip():
        overall_legal_summary = summarize_overall_legal_findings_with_bielik(combined_analyses_for_overall_summary)
        print("\n\n--- GLOBALNE PODSUMOWANIE PRAWNE (BIELIK - dla wszystkich dokumentów) ---")
        if overall_legal_summary and overall_legal_summary.strip():
            print(overall_legal_summary)
            global_summary_file_path = os.path.join(OUTPUT_FOLDER,
                                                    f"GLOBAL_BIELIK_SUMMARY_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            try:
                with open(global_summary_file_path, "w", encoding="utf-8") as f:
                    f.write(overall_legal_summary)
                print(f"\nGlobalne podsumowanie (BIELIK) zapisano do: {global_summary_file_path}")
            except Exception as e:
                print(f"BŁĄD (BIELIK): Nie można zapisać globalnego podsumowania: {e}")
        else:
            print("[BRAK GLOBALNEGO PODSUMOWANIA OD BIELIKA - MOŻLIWY PROBLEM Z API LUB BRAK TREŚCI DO PODSUMOWANIA]")
    else:
        print("[BRAK TREŚCI Z INDYWIDUALNYCH ANALIZ DO STWORZENIA GLOBALNEGO PODSUMOWANIA BIELIK]")

    print("------------------------------------------------------------------\n")

    write_usage_summary(processed_files_count, total_processing_duration)


if __name__ == "__main__":
    # Sprawdzenie, czy serwer Ollama jest dostępny przed uruchomieniem
    try:
        conn_test = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=None)
        conn_test.request("GET", "/api/tags")  # Proste zapytanie, aby sprawdzić czy serwer odpowiada
        response_test = conn_test.getresponse()
        if response_test.status == 200:
            print(f"Pomyślnie połączono z serwerem Ollama/BIELIK na {OLLAMA_HOST}:{OLLAMA_PORT}.")
            conn_test.close()
            process_all_pdfs_with_bielik()
        else:
            print(
                f"BŁĄD: Nie można uzyskać poprawnej odpowiedzi od serwera Ollama/BIELIK na {OLLAMA_HOST}:{OLLAMA_PORT}. Status: {response_test.status}")
            print("Upewnij się, że serwer Ollama jest uruchomiony i model BIELIK jest dostępny.")
        conn_test.close()
    except ConnectionRefusedError:
        print(f"KRYTYCZNY BŁĄD: Nie można połączyć się z serwerem Ollama/BIELIK na {OLLAMA_HOST}:{OLLAMA_PORT}.")
        print("Upewnij się, że serwer Ollama jest uruchomiony.")
    except Exception as e_conn_test:
        print(f"Wystąpił nieoczekiwany błąd podczas próby połączenia z Ollama/BIELIK: {e_conn_test}")

