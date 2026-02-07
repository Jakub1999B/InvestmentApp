from openai import OpenAI
import os

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY")
)

def call_llm(messages):
    return client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=messages
    )

