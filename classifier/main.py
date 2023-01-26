import collections
from fastapi import FastAPI
from transformers import pipeline
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

classifiers = {}


def get_classifier(label: str):
    global classifiers
    if label not in classifiers:
        classifiers[label] = pipeline(
            "sentiment-analysis", model=f"./classifier/models/{label}"
        )
    return classifiers[label]


@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    return {"message": "Hello world"}


@app.get("/predict/{label}")
async def predict(label: str, text: str):
    classifier = get_classifier(label)
    return classifier(text)
