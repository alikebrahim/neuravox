#!/usr/bin/env python3
"""
Generate sample audio files for testing the neuravox platform
"""
import numpy as np
import soundfile as sf
from pathlib import Path
import argparse


def generate_sine_wave(frequency: float, duration: float, sample_rate: int = 16000) -> np.ndarray:
    """Generate a sine wave at the given frequency"""
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    return 0.3 * np.sin(2 * np.pi * frequency * t)


def generate_test_audio_files(output_dir: Path):
    """Generate various test audio files"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test 1: Short continuous audio (10 seconds, no silence)
    print("Generating test_continuous_10s.wav...")
    audio = generate_sine_wave(440, 10)
    sf.write(output_dir / "test_continuous_10s.wav", audio, 16000)
    
    # Test 2: Audio with single silence gap (30 seconds total)
    print("Generating test_single_gap_30s.wav...")
    audio = np.zeros(30 * 16000)
    audio[0:10*16000] = generate_sine_wave(440, 10)  # First 10 seconds
    # 10 seconds of silence
    audio[20*16000:30*16000] = generate_sine_wave(880, 10)  # Last 10 seconds
    sf.write(output_dir / "test_single_gap_30s.wav", audio, 16000)
    
    # Test 3: Audio with multiple silence gaps (2 minutes)
    print("Generating test_multiple_gaps_2min.wav...")
    audio = np.zeros(120 * 16000)
    segments = [
        (0, 15, 440),      # 0-15s: 440Hz
        (40, 55, 880),     # 40-55s: 880Hz (25s gap)
        (85, 100, 660),    # 85-100s: 660Hz (30s gap)
        (105, 120, 550)    # 105-120s: 550Hz (5s gap - should merge with previous)
    ]
    for start, end, freq in segments:
        audio[start*16000:end*16000] = generate_sine_wave(freq, end-start)
    sf.write(output_dir / "test_multiple_gaps_2min.wav", audio, 16000)
    
    # Test 4: Very short audio (3 seconds)
    print("Generating test_very_short_3s.wav...")
    audio = generate_sine_wave(440, 3)
    sf.write(output_dir / "test_very_short_3s.wav", audio, 16000)
    
    # Test 5: Audio with varying amplitudes (simulating speech)
    print("Generating test_varying_amplitude_1min.wav...")
    duration = 60
    t = np.linspace(0, duration, duration * 16000, False)
    # Create envelope that varies amplitude
    envelope = 0.5 + 0.3 * np.sin(2 * np.pi * 0.1 * t)  # Slow variation
    audio = envelope * np.sin(2 * np.pi * 440 * t)
    # Add some quiet sections
    audio[20*16000:25*16000] *= 0.01  # Very quiet but not silent
    audio[45*16000:50*16000] *= 0.01
    sf.write(output_dir / "test_varying_amplitude_1min.wav", audio, 16000)
    
    # Test 6: Stereo audio file
    print("Generating test_stereo_20s.wav...")
    left_channel = generate_sine_wave(440, 20)
    right_channel = generate_sine_wave(550, 20)
    stereo_audio = np.column_stack((left_channel, right_channel))
    sf.write(output_dir / "test_stereo_20s.wav", stereo_audio, 16000)
    
    # Test 7: High sample rate audio (44.1kHz)
    print("Generating test_high_samplerate_10s.wav...")
    audio = generate_sine_wave(440, 10, sample_rate=44100)
    sf.write(output_dir / "test_high_samplerate_10s.wav", audio, 44100)
    
    # Test 8: Audio with long silence at the beginning and end
    print("Generating test_edge_silence_1min.wav...")
    audio = np.zeros(60 * 16000)
    audio[30*16000:40*16000] = generate_sine_wave(440, 10)  # 10s of audio in the middle
    sf.write(output_dir / "test_edge_silence_1min.wav", audio, 16000)
    
    # Generate different format files
    print("\nGenerating files in different formats...")
    test_audio = generate_sine_wave(440, 5)
    
    # FLAC format
    sf.write(output_dir / "test_format.flac", test_audio, 16000)
    
    # Generate a summary file
    summary = """# Test Audio Files

Generated test audio files for neuravox platform testing:

1. **test_continuous_10s.wav** - 10 seconds of continuous 440Hz tone (no silence)
2. **test_single_gap_30s.wav** - 30 seconds with one 10-second silence gap
3. **test_multiple_gaps_2min.wav** - 2 minutes with multiple silence gaps (25s+)
4. **test_very_short_3s.wav** - Very short 3-second file
5. **test_varying_amplitude_1min.wav** - 1 minute with varying amplitudes
6. **test_stereo_20s.wav** - 20 seconds of stereo audio
7. **test_high_samplerate_10s.wav** - 10 seconds at 44.1kHz sample rate
8. **test_edge_silence_1min.wav** - Audio with long silence at edges
9. **test_format.flac** - 5 seconds in FLAC format

All files use 16-bit PCM encoding unless otherwise noted.
"""
    
    with open(output_dir / "test_files_summary.md", "w") as f:
        f.write(summary)
    
    print(f"\n✓ Generated {len(list(output_dir.glob('*.wav'))) + len(list(output_dir.glob('*.flac')))} test audio files in {output_dir}")
    print(f"✓ See test_files_summary.md for details")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test audio files")
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path(__file__).parent / "fixtures",
        help="Output directory for test files (default: tests/fixtures)"
    )
    
    args = parser.parse_args()
    generate_test_audio_files(args.output_dir)