# an Async library for openai

import aiohttp
import functools
import json

@functools.lru_cache(maxsize=None)
def get_api_key():
    with open("openai_secrets.json") as f:
        secrets = json.load(f)
    return secrets["api_key"]


async def request(method, url, json=None, headers=None):
    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url, json=json, headers=headers) as response:
                return await response.json()
        elif method == 'POST':
            async with session.post(url, json=json, headers=headers) as response:
                return await response.json()

async def openai_request(method, url, params=None, headers=None):
    headers["Authorization"] = "Bearer " + get_api_key()
    return await request(method, url, params, headers)

async def list_models():
    url = "https://api.openai.com/v1/models"
    return await openai_request("GET", url)

async def get_model(model):
    url = "https://api.openai.com/v1/models/" + model
    return await openai_request("GET", url)

async def create_completion(prompt, engine="text-davinci-003", max_tokens=200, temperature=0, top_p=1, frequency_penalty=0, presence_penalty=0):
    url = "https://api.openai.com/v1/completions"
    headers = {"Content-Type": "application/json"}
    json = {
        "model": engine,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty
    }
    try:
        r = await openai_request("POST", url, json, headers)
    except aiohttp.client_exceptions.ContentTypeError:
        return None
    return r