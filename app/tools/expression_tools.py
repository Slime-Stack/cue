import json


def synthesize_speech(text: str, language: str, voice_name: str, speaking_rate: float, pitch: float) -> dict:
    """Synthesize speech from text using Google Cloud TTS.

    Args:
        text: The text to speak aloud.
        language: Language code, e.g. "en-US".
        voice_name: Google Cloud TTS voice name, e.g. "en-US-Journey-O".
        speaking_rate: Speaking rate from 0.25 to 4.0, where 1.0 is normal speed.
        pitch: Voice pitch from -20.0 to 20.0, where 0.0 is default.

    Returns:
        A dict with status, the spoken text, and audio details.
    """
    # TODO: Integrate Google Cloud TTS API
    # For now, return a stub that confirms what would be spoken
    return {
        "status": "success",
        "text_spoken": text,
        "voice": voice_name,
        "language": language,
        "speaking_rate": speaking_rate,
        "pitch": pitch,
        "audio_url": None,
    }


def complete_grammar(words: str, ability_level: int, user_age: int) -> dict:
    """Expand a sequence of selected AAC words into a grammatically complete sentence.

    Args:
        words: Space-separated words the user selected, e.g. "I want pizza".
        ability_level: User's ability level from 1 to 5.
        user_age: User's age in years.

    Returns:
        A dict with the original words and the completed sentence.
    """
    # The LLM handles grammar completion via its instruction.
    # This tool exists so the agent can be explicitly invoked for grammar tasks.
    return {
        "original_words": words,
        "ability_level": ability_level,
        "user_age": user_age,
    }


def format_for_texting(text: str, style: str) -> dict:
    """Format a sentence for text messaging with appropriate emoji and tone.

    Args:
        text: The grammatically complete sentence to format.
        style: Formatting style — one of "casual", "formal", or "emoji".

    Returns:
        A dict with the formatted text message.
    """
    # The LLM handles formatting via its instruction.
    # This tool provides structure for the agent to return formatted output.
    return {
        "original_text": text,
        "style": style,
    }
