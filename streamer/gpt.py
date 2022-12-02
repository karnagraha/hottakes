import functools
import json
import re

from . import asyncopenai as openai

async def send_yn_prompt(prompt):
    r = await send_prompt(prompt)
    if "yes" in r.lower():
        return True
    return False

async def send_rate_prompt(prompt):
    r = await send_prompt(prompt)
    r = r.strip()
    if re.match(r"^[0-9]+$", r):
        return int(r)
    return 0


async def send_prompt(prompt):
    response = await openai.create_completion(
        prompt=prompt,
        engine="text-davinci-003",
        temperature=0.9,
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    r = response["choices"][0]["text"]
    return r
