import aiohttp
import asyncio
import glog as log
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
import urllib.parse


async def _request(method, url):
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url) as response:
            return await response.json()


async def predict(label, text):
    """Predict whether a text is a match or not for a given label."""
    # text needs to be url encoded
    text = urllib.parse.quote(text, safe="")  # safe='' so / is encoded
    url = f"http://localhost:8000/predict/{label}?text={text}"
    try:
        response = await _request("GET", url)
    except (ClientConnectorError, ContentTypeError) as e:
        response = str(e)

    if isinstance(response, list):
        return response[0]
    else:
        log.info(f"Unexpected response while requesting {url}: {response}")
        return None
