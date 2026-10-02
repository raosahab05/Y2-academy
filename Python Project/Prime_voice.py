import speech_recognition as sr


# Create speech recognizer
recognizer = sr.Recognizer()


print("================================")
print("       PRIME VOICE TEST")
print("================================")

print("PRIME: Microphone test starting...")
print("PRIME: Please speak after the message.")


try:

    # Connect to microphone
    with sr.Microphone() as source:

        print("\nPRIME: Adjusting microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        print("PRIME: Listening...")
        print("You: ", end="")

        audio = recognizer.listen(
            source,
            timeout=5,
            phrase_time_limit=7
        )


    print("\nPRIME: Processing your voice...")

    # Convert voice to text
    text = recognizer.recognize_google(audio)

    print("PRIME: I heard:", text)


except sr.WaitTimeoutError:

    print("\nPRIME: I didn't hear anything.")


except sr.UnknownValueError:

    print("\nPRIME: Sorry, I couldn't understand your voice.")


except sr.RequestError:

    print(
        "\nPRIME: Speech recognition service "
        "is not available."
    )


except Exception as error:

    print("\nPRIME: Something went wrong.")
    print("Error:", error)