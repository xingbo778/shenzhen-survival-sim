#!/usr/bin/env python3
"""
Grok Image Generator - 使用 xAI Grok-2-Image API 生成图片
"""

import os
import requests
import logging

log = logging.getLogger("grok_image")

XAI_API_KEY = os.environ.get("XAI_API_KEY", "xai-nEhwehTvY3UTrB0RpuDvkspHMMziJ9StfrPvQLaCXKHxCWT5w1ufUiUwpLPCVNstR01pynhDB902ybvB")
XAI_API_URL = "https://api.x.ai/v1/images/generations"
XAI_MODEL = "grok-2-image"


def generate_image(prompt: str, save_path: str, api_key: str = None) -> dict:
    """
    生成图片并保存到本地。
    
    Args:
        prompt: 图片描述（英文效果更好）
        save_path: 本地保存路径
        api_key: xAI API Key（可选，默认从环境变量读取）
    
    Returns:
        {"success": True/False, "url": "...", "local_path": "...", "error": "..."}
    """
    key = api_key or XAI_API_KEY
    if not key:
        return {"success": False, "error": "No API key provided"}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": XAI_MODEL,
        "prompt": prompt,
        "n": 1
    }

    try:
        log.info(f"Generating image: {prompt[:80]}...")
        resp = requests.post(XAI_API_URL, headers=headers, json=payload, timeout=120)

        if resp.status_code != 200:
            error_msg = resp.text[:300]
            log.error(f"API error {resp.status_code}: {error_msg}")
            return {"success": False, "error": f"API {resp.status_code}: {error_msg}"}

        data = resp.json()
        image_url = data["data"][0]["url"]

        # 下载图片
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            log.info(f"Image saved to {save_path}")
            return {"success": True, "url": image_url, "local_path": save_path}
        else:
            return {"success": False, "url": image_url, "error": f"Download failed: {img_resp.status_code}"}

    except Exception as e:
        log.error(f"Image generation failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A cute cat taking a selfie"
    save = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/selfies/test.jpg"
    result = generate_image(prompt, save)
    print(result)
