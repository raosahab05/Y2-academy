import speech_recognition as sr
import datetime
import sys

recognizer = sr.Recognizer()


def speak(text):
    print("PRIME:", text)


def listen():
    with sr.Microphone() as source:
        print("PRIME: Listening...")

        try:
            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=8
            )

            print("PRIME: Processing your voice...")

            try:
                text = recognizer.recognize_google(audio)
                print("You:", text)
                return text.lower()

            except sr.UnknownValueError:
                print("PRIME: Sorry, I could not understand your voice.")
                return None

            except sr.RequestError as error:
                print("PRIME: Speech recognition service error.")
                print("Actual error:", repr(error))
                return None

        except sr.WaitTimeoutError:
            print("PRIME: I didn't hear anything.")
            return None

        except OSError as error:
            print("PRIME: Microphone/device error.")
            print("Error:", error)
            return None

        except Exception as error:
            print("PRIME: Unexpected voice recognition error.")
            print("Error:", error)
            return None


def process_command(command):

    if command is None:
        return

    if "hello prime" in command or "hi prime" in command:
        speak("Hello! How can I help you?")

    elif "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {current_time}")

    elif "date" in command:
        current_date = datetime.datetime.now().strftime("%d %B %Y")
        speak(f"Today's date is {current_date}")

    elif "exit" in command or "quit" in command or "stop" in command:
        speak("Goodbye!")
        sys.exit()

    else:
        speak("I heard you, but I don't know that command yet.")


def main():

    print("================================")
    print("       PRIME VOICE TEST")
    print("================================")

    print("PRIME: Microphone test starting...")
    print("PRIME: Please speak after the message.\n")

    while True:
        command = listen()
        process_command(command)


if __name__ == "__main__":
    main()