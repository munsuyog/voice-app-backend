"""
Minimal Chatterbox TTS example
Python 3.11 required
"""

import numpy as np
import soundfile as sf
from chatterbox.tts_turbo import ChatterboxTurboTTS

# Load model (NO arguments)
tts = ChatterboxTurboTTS.from_pretrained("cpu")

# Warm-up
tts.generate("warmup")

def text_to_audio(text: str, out_path: str = "output.wav"):
    audio = tts.generate(
        text=text
    )

    # 🔧 FIX: normalize audio for libsndfile
    if hasattr(audio, "cpu"):  # torch tensor
        audio = audio.cpu().numpy()

    audio = np.asarray(audio, dtype=np.float32)

    # Flatten (handles [1, N] or [N, 1])
    if audio.ndim > 1:
        audio = audio.reshape(-1)

    sf.write(
        out_path,
        audio,
        samplerate=24000,
        format="WAV",
        subtype="PCM_16"
    )

    print(f"Audio written to {out_path}")

if __name__ == "__main__":
    text_to_audio(
        "Hello! This audio was generated locally using Chatterbox text to speech. [chuckle]",
        "chatterbox_output.wav"
    )
