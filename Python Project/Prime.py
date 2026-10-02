import subprocess
import webbrowser
import datetime
import os


# =========================================================
#                    PRIME ASSISTANT
# =========================================================

print("========================================")
print("          PRIME ASSISTANT")
print("========================================")

print("PRIME: Hello! I am ready.")
print("PRIME: Type 'help' to see my commands.")
print("PRIME: Type 'exit' to close me.")


# =========================================================
#                    MAIN LOOP
# =========================================================

while True:

    command = input("\nYou: ").lower().strip()


    # =====================================================
    # HELLO
    # =====================================================

    if "hello" in command or "hi" in command:

        print("PRIME: Hello! How can I help you?")


    # =====================================================
    # HOW ARE YOU
    # =====================================================

    elif "how are you" in command:

        print("PRIME: I am doing great. Thanks for asking!")


    # =====================================================
    # WHO ARE YOU
    # =====================================================

    elif "who are you" in command:

        print(
            "PRIME: I am PRIME, your Python-based "
            "desktop assistant."
        )


    # =====================================================
    # CALCULATOR
    # =====================================================

    elif (
        "calculator" in command
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening Calculator...")

        subprocess.Popen("calc.exe")


    # =====================================================
    # NOTEPAD
    # =====================================================

    elif (
        "notepad" in command
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening Notepad...")

        subprocess.Popen("notepad.exe")


    # =====================================================
    # PAINT
    # =====================================================

    elif (
        "paint" in command
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening Paint...")

        subprocess.Popen("mspaint.exe")


    # =====================================================
    # FILE EXPLORER
    # =====================================================

    elif (
        ("explorer" in command or "file explorer" in command)
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening File Explorer...")

        subprocess.Popen("explorer.exe")


    # =====================================================
    # COMMAND PROMPT
    # =====================================================

    elif (
        ("cmd" in command or "command prompt" in command)
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening Command Prompt...")

        subprocess.Popen("cmd.exe")


    # =====================================================
    # CHROME
    # =====================================================

    elif (
        ("chrome" in command or "browser" in command)
        and any(
            word in command
            for word in ["open", "khol", "start", "chala", "run"]
        )
    ):

        print("PRIME: Opening Chrome...")

        chrome_paths = [

            r"C:\Program Files\Google\Chrome\Application\chrome.exe",

            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

        ]

        chrome_opened = False

        for path in chrome_paths:

            if os.path.exists(path):

                subprocess.Popen(path)

                chrome_opened = True

                break

        if not chrome_opened:

            print("PRIME: Chrome was not found.")


    # =====================================================
    # YOUTUBE
    # =====================================================

    elif "youtube" in command:

        print("PRIME: Opening YouTube...")

        webbrowser.open(
            "https://www.youtube.com"
        )


    # =====================================================
    # GOOGLE
    # =====================================================

    elif (
        "google" in command
        and "search" not in command
    ):

        print("PRIME: Opening Google...")

        webbrowser.open(
            "https://www.google.com"
        )


    # =====================================================
    # GOOGLE SEARCH
    # =====================================================

    elif (
        "search" in command
        or "google par" in command
    ):

        search_text = command

        remove_words = [
            "google",
            "par",
            "search",
            "karo",
            "kar",
            "do",
            "please",
            "bhai",
            "zara",
            "mujhe"
        ]

        for word in remove_words:

            search_text = search_text.replace(
                word,
                ""
            )

        search_text = search_text.strip()

        if search_text:

            search_url = (
                "https://www.google.com/search?q="
                + search_text.replace(" ", "+")
            )

            print(
                f"PRIME: Searching Google for {search_text}..."
            )

            webbrowser.open(search_url)

        else:

            print(
                "PRIME: What should I search for?"
            )


    # =====================================================
    # TIME
    # =====================================================

    elif "time" in command:

        current_time = datetime.datetime.now().strftime(
            "%I:%M %p"
        )

        print(
            f"PRIME: The current time is {current_time}."
        )


    # =====================================================
    # DATE
    # =====================================================

    elif "date" in command:

        current_date = datetime.datetime.now().strftime(
            "%d %B %Y"
        )

        print(
            f"PRIME: Today's date is {current_date}."
        )


    # =====================================================
    # HELP
    # =====================================================

    elif "help" in command:

        print("""
========================================
             PRIME COMMANDS
========================================

Applications:

    calculator kholo
    notepad kholo
    paint kholo
    chrome kholo
    file explorer kholo
    cmd kholo

Web:

    youtube kholo
    google kholo

Search:

    google par python search karo
    search python tutorial

Information:

    time kya hai
    date kya hai

Other:

    hello
    who are you
    how are you
    help
    exit

========================================
""")


    # =====================================================
    # EXIT
    # =====================================================

    elif (
        command == "exit"
        or "close prime" in command
        or "prime band" in command
    ):

        print("PRIME: Goodbye! See you later.")

        break


    # =====================================================
    # UNKNOWN COMMAND
    # =====================================================

    else:

        print(
            "PRIME: I don't understand that command yet."
        )