# -*- coding: utf-8 -*-

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
        setattr(self.listener, event, callback)


class TestStream(TestMixin, Stream):
    pass


class TestByteStream(TestMixin, ByteStream):
    pass
