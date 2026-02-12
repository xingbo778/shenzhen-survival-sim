---
name: grok-image-generator
description: Generate images using the xAI Grok-2-Image API. Provides a simple Python function to generate images from text prompts and save them locally.
---

# Grok Image Generator Skill

Generate images using xAI's Grok-2-Image model via their OpenAI-compatible API.

## API Details

- **Endpoint**: `POST https://api.x.ai/v1/images/generations`
- **Model**: `grok-2-image`
- **Auth**: Bearer token in Authorization header
- **Response**: Returns a JSON with `data[].url` containing the image URL

## Usage

```python
from skills.grok_image_generator.scripts.generate_image import generate_image

# Generate an image
result = generate_image(
    prompt="A young woman taking a selfie at Shenzhen Bay Park",
    api_key="your-xai-api-key",
    save_path="/path/to/output.jpg"
)
# result = {"success": True, "url": "https://...", "local_path": "/path/to/output.jpg"}
```

## Direct API Call

```python
import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

payload = {
    "model": "grok-2-image",
    "prompt": "your prompt here",
    "n": 1
}

r = requests.post("https://api.x.ai/v1/images/generations", headers=headers, json=payload, timeout=120)
data = r.json()
image_url = data["data"][0]["url"]
```

## Notes

- Do NOT pass `size` parameter — it's not supported and will return 400
- Image URLs are temporary; download and save locally
- Typical generation time: 5-15 seconds
- The model handles Chinese descriptions well but English prompts tend to produce better results
