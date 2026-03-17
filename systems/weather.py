import random
from core.world_state import world, log
from core.constants import WEATHER_TYPES, WEATHER_TRANSITION


def update_weather():
    """每个虚拟日的6:00更新天气"""
    current = world["weather"]["current"]
    candidates = WEATHER_TRANSITION.get(current, ["多云"])
    new_weather = random.choice(candidates)
    info = WEATHER_TYPES[new_weather]
    world["weather"] = {
        "current": new_weather,
        "desc": info["desc"],
        "changed_at_tick": world["time"]["tick"],
    }
    log.info(f"🌤️ 天气变化: {current} -> {new_weather} ({info['desc']})")
