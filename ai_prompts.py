from __future__ import annotations

import json
from pathlib import Path


PROMPTS_PATH = Path(__file__).with_name('ai_prompts.json')
PROMPT_KEYS = (
    'AI_CHAT_SYSTEM_PROMPT',
    'AI_STREAM_SYSTEM_PROMPT',
    'AI_REPAIR_SYSTEM_PROMPT',
)


def load_ai_prompts() -> dict[str, str]:
    with PROMPTS_PATH.open(encoding='utf-8') as file:
        prompts = json.load(file)

    missing_or_invalid = [
        key for key in PROMPT_KEYS
        if not isinstance(prompts.get(key), str) or not prompts[key].strip()
    ]
    if missing_or_invalid:
        names = ', '.join(missing_or_invalid)
        raise RuntimeError(f'Missing AI prompt(s) in {PROMPTS_PATH.name}: {names}')

    return {key: prompts[key].strip() for key in PROMPT_KEYS}


_PROMPTS = load_ai_prompts()

AI_CHAT_SYSTEM_PROMPT = _PROMPTS['AI_CHAT_SYSTEM_PROMPT']
AI_STREAM_SYSTEM_PROMPT = _PROMPTS['AI_STREAM_SYSTEM_PROMPT']
AI_REPAIR_SYSTEM_PROMPT = _PROMPTS['AI_REPAIR_SYSTEM_PROMPT']
