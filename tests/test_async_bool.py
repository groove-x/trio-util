from trio_util import AsyncBool


async def test_bool_event():
    event = AsyncBool()
    assert event.value is False
    await event.wait_value(False)
