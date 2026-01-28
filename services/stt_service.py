from openai import OpenAI
from pathlib import Path
from services.openai_service import client
def audio_to_text(audio_file_path: str) -> str:
	"""
	Converts audio file to text using Whisper
	"""
	with open(audio_file_path, "rb") as audio_file:
		transcription = client.audio.transcriptions.create(
			file=audio_file,
			model="gpt-4o-transcribe"
		)

	return transcription.text
