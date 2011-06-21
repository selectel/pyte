# -*- coding: utf-8 -*-

from collections import defaultdict
from pyte import Stream, ByteStream


class TestMixin(object):
    """A mixin which allows explicit subscription to a subset of events."""

    def connect(self, event, callback):
        """Add an event listener for a particular event.

        Depending on the event, there may or may not be parameters
        passed to the callback. Some escape sequences might also have
        default values, but providing these defaults is responsibility
        of the callback.

        :param unicode event: event to listen for.
        :param callable callback: callable to invoke when a given event
                                  occurs.
        """
        self.listeners[event].append(callback)

    def dispatch(self, event, *args, **kwargs):
        """Dispatch an event.

        .. note::

           If any callback throws an exception, the subsequent callbacks
           are be aborted.

        :param unicode event: event to dispatch.
        :param bool reset: reset stream state after all callback are
                           executed.
        :param list args: arguments to pass to event handlers.
        """
        for callback in self.listeners.get(event, []):
            callback(*args, **self.flags)
        else:
            if kwargs.get("reset", True): self.reset()


class TestStream(TestMixin, Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.listeners = defaultdict(lambda: [])


class TestByteStream(TestMixin, ByteStream):
    def __init__(self, *args, **kwargs):
        ByteStream.__init__(self, *args, **kwargs)
        self.listeners = defaultdict(lambda: [])
