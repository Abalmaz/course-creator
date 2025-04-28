import os
import tempfile
from pathlib import Path
from openai import OpenAI
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
# Ensure OPENAI_API_KEY is set as an environment variable
client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment variables. TTS functionality will not work.")

def generate_voiceover(text: str, voice: str = "alloy", output_format: str = "mp3") -> tuple[str, bytes]:
    """
    Generate a voiceover audio file from text using OpenAI's TTS API.
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (alloy, echo, fable, onyx, nova, or shimmer)
        output_format: The audio format (mp3 or opus)
        
    Returns:
        A tuple containing (file_path, audio_data) or (None, None) if error
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate voiceover.")
        return None, None
        
    if not text:
        logger.error("Empty text provided for voiceover generation.")
        return None, None
        
    # Validate voice option
    valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    if voice not in valid_voices:
        logger.warning(f"Invalid voice '{voice}'. Using default 'alloy'.")
        voice = "alloy"
        
    # Validate format option
    valid_formats = ["mp3", "opus"]
    if output_format not in valid_formats:
        logger.warning(f"Invalid format '{output_format}'. Using default 'mp3'.")
        output_format = "mp3"
    
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format=output_format
        )
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as temp_file:
            # Get the binary content
            audio_data = response.content
            # Write to the temporary file
            temp_file.write(audio_data)
            temp_file.flush()
            
            # Return the file path and the binary data
            return temp_file.name, audio_data
            
    except Exception as e:
        logger.error(f"Error generating voiceover from OpenAI: {e}")
        return None, None

def save_voiceover(audio_data: bytes, file_path: str) -> bool:
    """
    Save audio data to a file.
    
    Args:
        audio_data: The binary audio data
        file_path: The path where to save the file
        
    Returns:
        True if successful, False otherwise
    """
    if not audio_data:
        logger.error("No audio data provided to save.")
        return False
        
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write the audio data to the file
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        return True
    except Exception as e:
        logger.error(f"Error saving voiceover file: {e}")
        return False
