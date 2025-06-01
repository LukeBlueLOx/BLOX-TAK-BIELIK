# standard imports for LibreOffice macros
import uno
import unohelper
import json
import http.client  # For making HTTP requests


# Main macro function to correct text using Ollama
# Główna funkcja makra do poprawiania tekstu za pomocą Ollamy
def correct_text_with_ollama(*args):
    # Get the current document
    # Pobierz bieżący dokument
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    if not model:
        print("ERROR: No document open.")
        print("BŁĄD: Brak otwartego dokumentu.")
        return

    # Get the document controller and selection
    # Pobierz kontroler dokumentu i zaznaczenie
    controller = model.getCurrentController()
    if not controller:
        print("ERROR: No document controller available.")
        print("BŁĄD: Brak kontrolera dokumentu.")
        return

    selection = controller.getSelection()
    selected_text_original = ""  # Variable to store the text to be sent to Ollama
    selection_object = None  # Variable to store the actual selection object for later replacement

    # Try to get the selected text
    # Spróbuj pobrać zaznaczony tekst
    if hasattr(selection, 'getString') and selection.supportsService("com.sun.star.text.TextRange"):
        selected_text_original = selection.getString()
        selection_object = selection
        print("INFO: Text acquired from current selection (TextRange).")
        print("INFO: Tekst pobrany z bieżącego zaznaczenia (TextRange).")
    elif hasattr(selection, 'hasElements') and selection.hasElements():
        # Handle multiple selections or complex selections (e.g., table cells)
        # Obsługa wielokrotnych zaznaczeń lub złożonych zaznaczeń (np. komórek tabeli)
        text_builder = []
        try:
            for i in range(selection.getCount()):
                element = selection.getByIndex(i)
                if hasattr(element, 'getString') and element.supportsService("com.sun.star.text.TextRange"):
                    text_builder.append(element.getString())
                elif hasattr(element, 'getText') and element.getText().supportsService("com.sun.star.text.XText"):
                    text_builder.append(element.getText().getString())
                else:
                    print(f"DEBUG: Selected element type {type(element)} is not a recognizable text type. Skipping.")
                    print(
                        f"DEBUG: Typ zaznaczonego elementu {type(element)} nie jest rozpoznawalnym typem tekstowym. Pomijam.")
            selected_text_original = "\n".join(text_builder)
            selection_object = selection  # Keep the original complex selection object for replacement
            print("INFO: Text acquired from complex selection (XIndexAccess).")
            print("INFO: Tekst pobrany ze złożonego zaznaczenia (XIndexAccess).")
        except Exception as e:
            print(f"WARNING: Error iterating through complex selection: {e}. Falling back to entire document.")
            print(
                f"OSTRZEŻENIE: Błąd podczas iteracji przez złożone zaznaczenie: {e}. Zamiast tego używam całego dokumentu.")
            selected_text_original = ""  # Reset to force full document text
    else:
        print("INFO: No valid text selection found or selection is not directly text-like.")
        print("INFO: Nie znaleziono prawidłowego zaznaczenia tekstu lub zaznaczenie nie jest bezpośrednio tekstowe.")

    # If no text was selected, get the entire document text
    # Jeśli nie zaznaczono tekstu, pobierz cały tekst dokumentu
    if not selected_text_original.strip():
        text_document_object = model.Text
        if not text_document_object:
            print("ERROR: Could not get the document's main text object.")
            print("BŁĄD: Nie można uzyskać głównego obiektu tekstu dokumentu.")
            return

        selected_text_original = text_document_object.getString()
        selection_object = text_document_object  # To will replace the entire document
        print("INFO: No text selection found. Acquiring entire document text.")
        print("INFO: Nie znaleziono zaznaczenia tekstu. Pobieram cały tekst dokumentu.")

    if not selected_text_original.strip():
        print("INFO: Document or selected text is empty. Nothing to correct.")
        print("INFO: Dokument lub zaznaczony tekst jest pusty. Brak tekstu do poprawy.")
        return

    print(f"Text to correct (first 100 characters): {selected_text_original[:100]}...")
    print(f"Tekst do poprawy (pierwsze 100 znaków): {selected_text_original[:100]}...")

    # --- Ollama API configuration ---
    # --- Konfiguracja API Ollamy ---
    OLLAMA_HOST = "localhost"  # or the IP address of your OrangePi if Ollama runs there
    # lub adres IP OrangePi, jeśli Ollama działa na nim
    OLLAMA_PORT = 11434
    MODEL_NAME = "bielik-4.5b-q4km-final"  # Ensure this is the name of your model in Ollama
    # Upewnij się, że to nazwa Twojego modelu w Ollamie

    # Prepare the prompt for Ollama exactly as it worked in the console
    # Przygotuj prompt dla Ollamy dokładnie tak, jak zadziałał w konsoli
    full_console_prompt = (
        f"BIELIKU, popraw błędy ortograficzne, gramatyczne i stylistyczne w poniższym tekście. "
        f"Upewnij się, że tekst jest poprawny językowo i naturalnie brzmiący po polsku. "
        f"Zwróć tylko poprawiony tekst, bez dodatkowych komentarzy. "
        f"Tekst do poprawy: {selected_text_original}"
    )

    messages_payload = [
        {'role': 'user', 'content': full_console_prompt}
    ]

    try:
        # Connect to Ollama API
        # Połącz się z API Ollamy
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT)
        headers = {'Content-Type': 'application/json'}
        body = json.dumps({
            "model": MODEL_NAME,
            "messages": messages_payload,
            "stream": False  # Set to False for single response
            # Ustaw na False dla pojedynczej odpowiedzi
        })

        print(f"Sending request to Ollama API at http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat...")
        print(f"Wysyłam zapytanie do API Ollamy na http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/chat...")

        conn.request("POST", "/api/chat", body=body, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        conn.close()

        print(f"Ollama API Response Status: {response.status}")
        print(f"Status odpowiedzi API Ollamy: {response.status}")
        print(f"Full Ollama API Response (for diagnostics): {response_data}")
        print(f"Pełna odpowiedź API Ollamy (do diagnostyki): {response_data}")

        if response.status == 200:
            result = json.loads(response_data)

            # Extract corrected text from Ollama's response
            # Wyodrębnij poprawiony tekst z odpowiedzi Ollamy
            corrected_text = ""
            if 'message' in result and 'content' in result['message']:
                corrected_text = result['message']['content'].strip()

            if corrected_text:
                # Replace the original text (either selection or entire document) with the corrected text
                # Zastąp oryginalny tekst (zaznaczenie lub cały dokument) poprawionym tekstem
                if selection_object and hasattr(selection_object, 'setString'):
                    selection_object.setString(corrected_text)
                    print("SUCCESS: Text corrected successfully by Ollama!")
                    print("SUKCES: Tekst poprawiony pomyślnie przez Ollamę!")
                else:
                    print("ERROR: Could not replace text. Selection object is invalid or lacks setString method.")
                    print(
                        "BŁĄD: Nie można zastąpić tekstu. Obiekt zaznaczenia jest nieprawidłowy lub nie ma metody setString.")
            else:
                print("WARNING: Ollama returned an empty corrected text.")
                print("OSTRZEŻENIE: Ollama zwróciła pusty poprawiony tekst.")
        else:
            print(f"ERROR: Ollama server error: HTTP {response.status} - {response_data}")
            print(f"BŁĄD: Błąd serwera Ollamy: HTTP {response.status} - {response_data}")

    except Exception as e:
        print(f"CRITICAL ERROR: During communication with Ollama: {e}")
        print(f"KRYTYCZNY BŁĄD: Podczas komunikacji z Ollamą: {e}")


# Register the macro for LibreOffice (required for execution)
# Rejestracja makra dla LibreOffice (wymagane do wykonania)
g_exportedScripts = correct_text_with_ollama,