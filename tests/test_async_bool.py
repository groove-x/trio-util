from trio_util import AsyncBool


async def test_async_bool() -> None:
    event = AsyncBool()
    assert event.value is False
    await event.wait_value(False)
