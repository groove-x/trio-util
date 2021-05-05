from trio_util import AsyncBool


async def test_async_bool():
    event = AsyncBool()
    assert event.value is False
    await event.wait_value(False)
