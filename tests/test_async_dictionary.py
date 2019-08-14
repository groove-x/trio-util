import trio
from trio_util import AsyncDictionary

async def test_async_dictionary(nursery, autojump_clock):
    async def reader(d):
        assert await d.get_wait('bar') == 99
        assert 'bar' in d
        assert await d.pop_wait('baz') == 'done'
        assert 'baz' not in d
        with trio.move_on_after(.1):
            await d.get_wait('baz')
            assert False

    async def writer(d):
        await trio.sleep(.1)
        assert d.is_waiting('bar')
        d['bar'] = 99
        await trio.sleep(.1)
        assert d.is_waiting('baz')
        d['baz'] = 'done'

    d = AsyncDictionary(foo=10)
    assert len(d) == 1
    assert 'foo' in d
    assert [k for k in d] == ['foo']
    assert await d.get_wait('foo') == 10
    assert not d.is_waiting('foo')
    del d['foo']
    assert not d
    nursery.start_soon(reader, d)
    nursery.start_soon(writer, d)
