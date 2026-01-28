from openai import OpenAI
import os
from core.config import settings

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)
