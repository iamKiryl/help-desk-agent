import os
from pathlib import Path
import httpx
from google.genai import types

from dotenv import load_dotenv
from google import genai

from google.genai import errors


def main():
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    api_key = os.getenv("AI_API_KEY")
    model = os.getenv("AI_MODEL")

    if not api_key or not model:
        raise SystemExit(
            "Check you're AI_API_KEY and AI_MODEL in .env"
        )

    http_options = types.HttpOptions(
        timeout=60_000,
        retry_options=types.HttpRetryOptions(attempts=1),
    )

    print(f"Sending request to {model}...", flush=True)

    try:
        with genai.Client(
            api_key=api_key,
            http_options=http_options,
        ) as client:
            response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: Connection works",
        )
        print(response.text)

    except httpx.TimeoutException:
        print("Server did not respond within the allocated time.")

    except httpx.RequestError as error:
        print(f"Connection error: {type(error).__name__}")

    except errors.APIError as error:
        if error.code == 503:
            print("The model is overloaded. Please try again later.")
        elif error.code == 429:
            print("Request quota exceeded. Check your limits in AI Studio.")
        else:
            print(f"API error {error.code}: {error.message}")


if __name__ == "__main__":
    main()
