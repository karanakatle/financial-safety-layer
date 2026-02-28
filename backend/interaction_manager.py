def orchestrate_response(message, mode, language, voice_provider=None):
    """
    Decides how response should be delivered.
    """

    response = {
        "text": message,
        "speak": False,
        "popup": False,
        "chat": False,
        "audio": None
    }

    if mode == "voice":
        response["speak"] = True

        if voice_provider:
            response["audio"] = voice_provider.text_to_speech(message, language)

    elif mode == "chat":
        response["chat"] = True

    else:  # default nudges
        response["popup"] = True

    return response