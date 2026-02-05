"""
Utility to generate test audio files for unit testing.
"""
import numpy as np
import soundfile as sf
import os


def generate_test_audio(filename: str, duration: float = 2.0, sample_rate: int = 16000, audio_type: str = "sine"):
    """
    Generate synthetic audio test file.
    
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
    
    # Save as MP3 (soundfile will encode via ffmpeg if available)
    sf.write(filename, audio, sample_rate, format='wav')
    
    # Convert WAV to MP3 using ffmpeg if available
    os.system(f"ffmpeg -i {filename} -q:a 9 {filename.replace('.wav', '.mp3')} -y 2>/dev/null")
    if os.path.exists(filename):
        os.remove(filename)


if __name__ == "__main__":
    # Generate test files
    os.makedirs("tests/audio_samples", exist_ok=True)
    
    print("Generating test audio files...")
    generate_test_audio("tests/audio_samples/test_sine_2s.wav", duration=2.0, audio_type="sine")
    generate_test_audio("tests/audio_samples/test_noise_2s.wav", duration=2.0, audio_type="noise")
    generate_test_audio("tests/audio_samples/test_short_0.5s.wav", duration=0.5, audio_type="sine")
    generate_test_audio("tests/audio_samples/test_long_10s.wav", duration=10.0, audio_type="sine")
    
    print("Test audio files generated in tests/audio_samples/")
