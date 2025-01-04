"""ElevenLabs TTS plugin for OVOS."""
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from ovos_plugin_manager.templates.tts import TTS, TTSValidator
from ovos_utils.log import LOG


class OutputFormat(str, Enum):
    """Supported output formats."""
    MP3_44100_128 = "mp3_44100_128"
    MP3_44100_64 = "mp3_44100_64"
    MP3_22050_32 = "mp3_22050_32"


@dataclass
class TTSConfiguration:
    """Default configuration values for the TTS plugin."""
    DEFAULT_MODEL = "eleven_multilingual_v2"
    DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # Default voice "George"
    DEFAULT_STABILITY = 0.5
    DEFAULT_SIMILARITY = 0.75
    DEFAULT_STYLE = 0.0  # Ranges from 0-1, 0 is neutral
    DEFAULT_SPEAKER_BOOST = True
    DEFAULT_OUTPUT_FORMAT = OutputFormat.MP3_44100_128
    DEFAULT_USE_STREAMING = False


class ElevenLabsTTSPlugin(TTS):
    """TTS plugin for ElevenLabs."""

    # Define available_languages as a class variable instead of a property
    available_languages = {
        "en", "es", "fr", "de", "it", "pt", "pl", "hi",
        "ar", "bn", "cs", "da", "nl", "fi", "el", "hu",
        "id", "ja", "ko", "ms", "no", "ro", "ru", "sk",
        "sv", "ta", "tr", "uk", "ur", "vi", "zh", "bg"
    }

    def __init__(self, *args, **kwargs):
        LOG.debug("Initializing ElevenLabsTTS")
        try:
            super().__init__(*args, **kwargs, audio_ext="mp3",
                            validator=ElevenLabsTTSValidator(self))
            LOG.debug("Super init complete")
            self.client = ElevenLabs(api_key=self.api_key)
            LOG.debug("Client initialized")
        except Exception as e:
            LOG.error(f"Failed to initialize ElevenLabsTTS: {str(e)}")
            raise

    @property
    def api_key(self) -> str:
        """Get API key from config."""
        api_key = self.config.get("api_key") or os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ElevenLabs API key not found in config or environment")
        return api_key

    @property
    def voice_id(self) -> str:
        """Get voice ID from config."""
        voice_id = self.config.get("voice_id")
        # Log available voices to help troubleshoot
        try:
            voices = self.client.voices.get_all()
            # ElevenLabs API returns list of tuples, extract just the IDs
            available_voices = []
            for voice in voices:
                # Each voice is a tuple of (name, voice_id, ...)
                voice_info = voice[0] if isinstance(voice, tuple) else voice
                if hasattr(voice_info, "voice_id"):
                    available_voices.append((voice_info.name, voice_info.voice_id))
            LOG.debug(f"Available voices: {available_voices}")
        except Exception as e:
            LOG.warning(f"Could not fetch available voices: {str(e)}")

        # If no voice_id configured, use default
        if not voice_id:
            LOG.debug(f"No voice_id configured, using default: {TTSConfiguration.DEFAULT_VOICE_ID}")
            return TTSConfiguration.DEFAULT_VOICE_ID

        LOG.debug(f"Using configured voice_id: {voice_id}")
        return voice_id

    @property
    def model_id(self) -> str:
        """Get model ID from config."""
        return self.config.get("model_id", TTSConfiguration.DEFAULT_MODEL)

    @property
    def use_streaming(self) -> bool:
        """Whether to use streaming API."""
        return self.config.get("use_streaming", TTSConfiguration.DEFAULT_USE_STREAMING)

    @property
    def output_format(self) -> str:
        """Get output format from config."""
        return self.config.get("output_format", TTSConfiguration.DEFAULT_OUTPUT_FORMAT)

    @property
    def voice_settings(self) -> Dict[str, Any]:
        """Get voice settings from config."""
        return {
            "stability": self.config.get("stability", TTSConfiguration.DEFAULT_STABILITY),
            "similarity_boost": self.config.get("similarity_boost",
                                              TTSConfiguration.DEFAULT_SIMILARITY),
            "style": self.config.get("style", TTSConfiguration.DEFAULT_STYLE),
            "use_speaker_boost": self.config.get("speaker_boost",
                                               TTSConfiguration.DEFAULT_SPEAKER_BOOST)
        }

    def get_tts(self, sentence: str, wav_file: str,
            lang: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """Convert text to speech using ElevenLabs API."""
        try:
            # Ensure output path has .mp3 extension
            out_path = wav_file.replace(".wav", ".mp3")
            LOG.debug(f"Converting text to speech: {sentence[:20]}...")
            LOG.debug(f"Output path: {out_path}")
            LOG.debug(f"Using streaming: {self.use_streaming}")
            LOG.debug(f"Using voice_id: {self.voice_id}")

            # Validate voice ID before making API call
            try:
                voices = self.client.voices.get_all()
                # Extract voice IDs from the API response
                available_voice_ids = []
                for voice in voices:
                    # Each voice is a tuple of (name, voice_id, ...)
                    voice_info = voice[0] if isinstance(voice, tuple) else voice
                    if hasattr(voice_info, "voice_id"):
                        available_voice_ids.append(voice_info.voice_id)

                LOG.debug(f"Available voice IDs: {available_voice_ids}")
                if self.voice_id not in available_voice_ids:
                    raise ValueError(f"Voice ID {self.voice_id} not found in available voices")
            except Exception as e:
                LOG.error(f"Voice validation failed: {str(e)}")
                raise

            if self.use_streaming:
                # Streaming approach
                LOG.debug("Using streaming API")
                audio_stream = self.client.text_to_speech.convert_as_stream(
                    text=sentence,
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    output_format=self.output_format,
                    voice_settings=VoiceSettings(**self.voice_settings)
                )
            else:
                # Non-streaming approach still returns a generator
                LOG.debug("Using non-streaming API")
                audio_stream = self.client.text_to_speech.convert(
                    text=sentence,
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    output_format=self.output_format,
                    voice_settings=VoiceSettings(**self.voice_settings)
                )

            # Write stream to file - both approaches use the same write logic now
            LOG.debug("Writing audio stream to file")
            bytes_written = 0
            with open(out_path, "wb") as f:
                for chunk in audio_stream:
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
            LOG.debug(f"Successfully wrote {bytes_written} bytes to {out_path}")

            return out_path, None

        except Exception as e:
            LOG.error(f"ElevenLabs TTS error: {str(e)}")
            raise


class ElevenLabsTTSValidator(TTSValidator):
    """Validator for ElevenLabs TTS plugin."""

    def __init__(self, tts) -> None:
        super().__init__(tts)

    def validate_dependencies(self):
        """Validate required dependencies are installed."""
        try:
            import elevenlabs
        except ImportError:
            raise Exception(
                "ElevenLabs not installed. Please install with: "
                "pip install elevenlabs"
            )

    def validate_connection(self):
        """Validate connection to ElevenLabs API."""
        try:
            # Test connection by getting available models
            self.tts.client.models.get_all()
        except Exception as e:
            LOG.error(f"Error connecting to ElevenLabs API: {str(e)}")
            raise

    def validate_voice(self):
        """Validate the configured voice exists."""
        try:
            voices = self.tts.client.voices.get_all()
            voice_ids = [v.voice_id for v in voices]
            LOG.debug(f"Available voice IDs: {voice_ids}")
            LOG.debug(f"Configured voice ID: {self.tts.voice_id}")

            if self.tts.voice_id not in voice_ids:
                raise Exception(
                    f"Voice ID '{self.tts.voice_id}' not found in available voices: {voice_ids}"
                )
        except Exception as e:
            LOG.error(f"Error validating voice: {str(e)}")
            raise

    def validate_lang(self):
        """Validate language is supported."""
        # Extract primary language code before hyphen
        # e.g., "en-US" -> "en"
        primary_lang = self.tts.lang.split('-')[0].lower()
        if primary_lang not in self.tts.available_languages:
            raise ValueError(
                f"Language {self.tts.lang} not supported. "
                f"Supported languages: {self.tts.available_languages}"
            )

    def get_tts_class(self):
        """Return the TTS class."""
        return ElevenLabsTTSPlugin


# Sample valid configurations per language
ElevenLabsTTSConfig = {
    # Generate for all supported languages
    lang: [{
        "lang": lang,
        "display_name": f"ElevenLabs TTS ({lang})",
        "offline": False,
        "priority": 70,
        "model_id": TTSConfiguration.DEFAULT_MODEL,
        "voice_id": TTSConfiguration.DEFAULT_VOICE_ID,
        "stability": TTSConfiguration.DEFAULT_STABILITY,
        "similarity_boost": TTSConfiguration.DEFAULT_SIMILARITY,
        "style": TTSConfiguration.DEFAULT_STYLE,
        "speaker_boost": TTSConfiguration.DEFAULT_SPEAKER_BOOST,
        "use_streaming": TTSConfiguration.DEFAULT_USE_STREAMING,
        "output_format": TTSConfiguration.DEFAULT_OUTPUT_FORMAT
    }] for lang in ElevenLabsTTSPlugin.available_languages
}
