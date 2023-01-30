import pytest
from streamer.eventfilter import EventFilter


class FakeClassifier:
    def __init__(self, result="positive", score=0.9):
        self.result = result
        self.score = score

    async def predict(self, tag, text):
        return {
            "label": self.result,
            "score": self.score,
        }


class FakeRepeatDB:
    def __init__(self, result=False):
        self.result = result

    async def check_repeat(self, text):
        return self.result, None, None


def fake_event():
    return {
        "url": "htttps://invalid/1234",
        "text": "some text",
    }


@pytest.mark.asyncio
async def test_passthrough():
    """Test that the passthrough filter works."""
    ef = EventFilter("tag", channels=[], filter="", repeat_db=None, classifier=None)
    event = fake_event()
    result = await ef.handle_event(event)
    assert result
    assert event["url"] in result


@pytest.mark.asyncio
async def test_classifier_positive():
    classifier = FakeClassifier()
    ef = EventFilter(
        "tag", channels=[], filter="", repeat_db=None, classifier=classifier
    )
    event = fake_event()
    result = await ef.handle_event(event)
    assert result
    assert event["url"] in result


@pytest.mark.asyncio
async def test_classifier_negative():
    classifier = FakeClassifier(result="negative")
    ef = EventFilter(
        "tag", channels=[], filter="", repeat_db=None, classifier=classifier
    )
    event = fake_event()
    result = await ef.handle_event(event)
    assert not result


@pytest.mark.asyncio
async def test_classifier_norepeat():
    repeat_db = FakeRepeatDB(False)
    ef = EventFilter(
        "tag", channels=[], filter="", repeat_db=repeat_db, classifier=None
    )
    event = fake_event()
    result = await ef.handle_event(event)
    assert result
    assert event["url"] in result


@pytest.mark.asyncio
async def test_classifier_repeat():
    repeat_db = FakeRepeatDB(True)
    ef = EventFilter(
        "tag", channels=[], filter="", repeat_db=repeat_db, classifier=None
    )
    event = fake_event()
    result = await ef.handle_event(event)
    assert not result
