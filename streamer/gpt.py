import openai
import functools
import json

@functools.lru_cache(maxsize=None)
def get_api_key():
    with open("openai_secrets.json") as f:
        secrets = json.load(f)
    return secrets["api_key"]
openai.api_key = get_api_key()


def send_yn_prompt(prompt):
    r = send_prompt(prompt)
    if "yes" in r.lower():
        return True
    return False

def send_prompt(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.9,
        max_tokens=200,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        #stop=["---"],
    )
    r = response.choices[0].text
    return r
