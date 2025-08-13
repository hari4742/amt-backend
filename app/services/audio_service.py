"""
Audio processing service for audio analysis and preprocessing.
"""

import os
import librosa
import soundfile as sf
import numpy as np
from typing import Tuple, Optional, Dict, Any
from app.config import settings


class AudioService:
    """Service for audio processing and analysis."""

    @staticmethod
    def load_audio(file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file and return audio data and sample rate.

        Args:
            file_path: Path to the audio file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            # Load audio file
            audio_data, sample_rate = librosa.load(
                file_path,
                sr=settings.sample_rate,
                mono=True
            )
            return audio_data, sample_rate
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {str(e)}")

    @staticmethod
    def analyze_audio(audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        Analyze audio and extract features.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Dictionary containing audio analysis results
        """
        # Calculate duration
        duration = len(audio_data) / sample_rate

        # Check duration limit
        if duration > settings.max_audio_duration:
            raise ValueError(
                f"Audio duration ({duration:.2f}s) exceeds maximum allowed duration ({settings.max_audio_duration}s)")

        # Calculate RMS (Root Mean Square) for volume analysis
        rms = np.sqrt(np.mean(audio_data**2))

        # Calculate spectral features
        spectral_centroids = librosa.feature.spectral_centroid(
            y=audio_data, sr=sample_rate)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=audio_data, sr=sample_rate)[0]

        # Calculate tempo
        tempo, _ = librosa.beat.beat_track(y=audio_data, sr=sample_rate)

        # Calculate pitch features
        pitches, magnitudes = librosa.piptrack(y=audio_data, sr=sample_rate)

        # Get dominant frequencies
        dominant_frequencies = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                dominant_frequencies.append(pitch)

        # Calculate statistics
        analysis = {
            "duration": duration,
            "sample_rate": sample_rate,
            "rms": float(rms),
            "tempo": float(tempo),
            "spectral_centroid_mean": float(np.mean(spectral_centroids)),
            "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
            "dominant_frequency_mean": float(np.mean(dominant_frequencies)) if dominant_frequencies else 0.0,
            "dominant_frequency_std": float(np.std(dominant_frequencies)) if dominant_frequencies else 0.0,
            "is_silent": rms < 0.01,  # Threshold for silence detection
            "has_audio_content": rms > 0.001  # Minimum threshold for audio content
        }

        return analysis

    @staticmethod
    def preprocess_audio(audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Preprocess audio for transcription.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Preprocessed audio data
        """
        # Normalize audio
        audio_normalized = librosa.util.normalize(audio_data)

        # Apply high-pass filter to remove low-frequency noise
        audio_filtered = librosa.effects.preemphasis(audio_normalized, coef=0.97)

        # Trim silence from beginning and end
        audio_trimmed, _ = librosa.effects.trim(audio_filtered, top_db=20)

        return audio_trimmed

    @staticmethod
    def validate_audio_quality(audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, str]:
        """
        Validate audio quality for transcription.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if audio is too short
        duration = len(audio_data) / sample_rate
        if duration < 1.0:  # Less than 1 second
            return False, "Audio file is too short (less than 1 second)"

        # Check if audio is silent
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < 0.001:
            return False, "Audio file appears to be silent or too quiet"

        # Check for clipping
        if np.max(np.abs(audio_data)) > 0.99:
            return False, "Audio file appears to be clipped"

        # Check for excessive noise (low signal-to-noise ratio)
        # This is a simplified check - in practice, you might want more sophisticated noise detection
        spectral_centroids = librosa.feature.spectral_centroid(
            y=audio_data, sr=sample_rate)[0]
        if np.std(spectral_centroids) < 100:  # Low spectral variation might indicate noise
            return False, "Audio file appears to have low quality or excessive noise"

        return True, "Audio quality is acceptable"

    @staticmethod
    def extract_features_for_transcription(audio_data: np.ndarray, sample_rate: int) -> Dict[str, np.ndarray]:
        """
        Extract features needed for transcription.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio

        Returns:
            Dictionary containing extracted features
        """
        # Mel spectrogram (commonly used for music transcription)
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data,
            sr=sample_rate,
            n_mels=128,
            hop_length=512
        )

        # Convert to log scale
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Chromagram (useful for pitch detection)
        chromagram = librosa.feature.chroma_stft(
            y=audio_data,
            sr=sample_rate,
            hop_length=512
        )

        # MFCC features
        mfcc = librosa.feature.mfcc(
            y=audio_data,
            sr=sample_rate,
            n_mfcc=13,
            hop_length=512
        )

        # Onset strength
        onset_env = librosa.onset.onset_strength(
            y=audio_data,
            sr=sample_rate,
            hop_length=512
        )

        features = {
            "mel_spectrogram": mel_spec_db,
            "chromagram": chromagram,
            "mfcc": mfcc,
            "onset_strength": onset_env,
            "sample_rate": sample_rate,
            "hop_length": 512
        }

        return features

    @staticmethod
    def save_processed_audio(audio_data: np.ndarray, output_path: str, sample_rate: int) -> None:
        """
        Save processed audio to file.

        Args:
            audio_data: Audio data to save
            output_path: Output file path
            sample_rate: Sample rate of the audio
        """
        try:
            sf.write(output_path, audio_data, sample_rate)
        except Exception as e:
            raise ValueError(f"Failed to save processed audio: {str(e)}")
