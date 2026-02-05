"""
Utility to generate test audio files for unit testing.
"""
import numpy as np
import soundfile as sf
import os
import struct
import wave


def generate_test_audio(filename: str, duration: float = 2.0, sample_rate: int = 16000, audio_type: str = "sine"):
    """
    Generate synthetic audio test file (as WAV, saved with requested extension).
    
    Args:
        filename: Output file path
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        audio_type: "sine" (pure tone) or "noise" (white noise)
    """
    num_samples = int(duration * sample_rate)
    
    if audio_type == "sine":
        # Generate a sine wave at 440 Hz (A4 note)
        t = np.arange(num_samples) / sample_rate
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)
    elif audio_type == "noise":
        # Generate white noise
        audio = 0.1 * np.random.randn(num_samples)
    else:
        raise ValueError(f"Unknown audio type: {audio_type}")
    
    # Save as WAV internally, then move to requested filename
    wav_filename = filename.replace('.mp3', '.wav')
    sf.write(wav_filename, audio, sample_rate)
    
    # Rename to the requested filename (the API accepts WAV data with any extension)
    if wav_filename != filename:
        os.rename(wav_filename, filename)


if __name__ == "__main__":
    # Generate test files
    os.makedirs("tests/audio_samples", exist_ok=True)
    
    print("Generating test audio files...")
    generate_test_audio("tests/audio_samples/test_sine_2s.mp3", duration=2.0, audio_type="sine")
    generate_test_audio("tests/audio_samples/test_noise_2s.mp3", duration=2.0, audio_type="noise")
    generate_test_audio("tests/audio_samples/test_short_0.5s.mp3", duration=0.5, audio_type="sine")
    generate_test_audio("tests/audio_samples/test_long_10s.mp3", duration=10.0, audio_type="sine")
    
    print("Test audio files generated in tests/audio_samples/")
