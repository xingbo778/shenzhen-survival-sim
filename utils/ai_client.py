import os
from openai import OpenAI
import json

# World engine uses grok for image generation; OpenAI client is a placeholder
# (bot_agent.py uses the real key). Set a dummy key to avoid startup error.
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "placeholder"))

GROK_API_KEY = "xai-nEhwehTvY3UTrB0RpuDvkspHMMziJ9StfrPvQLaCXKHxCWT5w1ufUiUwpLPCVNstR01pynhDB902ybvB"


def grok_generate(prompt: str, save_path: str) -> dict:
    import requests as req
    try:
        resp = req.post(
            "https://api.x.ai/v1/images/generations",
            headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "grok-2-image", "prompt": prompt, "n": 1, "response_format": "url"},
            timeout=120,
        )
        data = resp.json()
        if "data" not in data or not data["data"]:
            return {"success": False, "error": f"API响应异常: {json.dumps(data, ensure_ascii=False)[:200]}"}
        url = data["data"][0]["url"]
        img = req.get(url, timeout=60)
        with open(save_path, "wb") as f:
            f.write(img.content)
        return {"success": True, "path": save_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
