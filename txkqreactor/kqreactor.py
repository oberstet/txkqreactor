# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
A kqueue()/kevent() based implementation of the Twisted main loop.

To install the event loop (and you should do this before any connections,
listeners or connectors are added)::

    | from twisted.internet import kqreactor
    | kqreactor.install()

This implementation depends on Python 2.6 or higher which has kqueue support
built in the select module.
"""

import errno, sys

from zope.interface import implements

from select import kqueue, kevent
from select import KQ_FILTER_READ, KQ_FILTER_WRITE, KQ_EV_DELETE, KQ_EV_ADD, KQ_EV_EOF

from twisted.internet.interfaces import IReactorFDSet

from twisted.python import log, failure
from twisted.internet import main, posixbase


class KQueueReactor(posixbase.PosixReactorBase):
    """
    A reactor that uses kqueue(2)/kevent(2) and relies on Python 2.6 or higher
    which has built in support for kqueue in the select module.

    @ivar _kq: A L{kqueue} which will be used to check for I/O readiness.

    @ivar _selectables: A dictionary mapping integer file descriptors to
        instances of L{FileDescriptor} which have been registered with the
        reactor.  All L{FileDescriptors} which are currently receiving read or
        write readiness notifications will be present as values in this
        dictionary.

    @ivar _reads: A dictionary mapping integer file descriptors to arbitrary
        values (this is essentially a set).  Keys in this dictionary will be
        registered with C{_kq} for read readiness notifications which will be
        dispatched to the corresponding L{FileDescriptor} instances in
        C{_selectables}.

    @ivar _writes: A dictionary mapping integer file descriptors to arbitrary
        values (this is essentially a set).  Keys in this dictionary will be
        registered with C{_kq} for write readiness notifications which will be
        dispatched to the corresponding L{FileDescriptor} instances in
        C{_selectables}.
    """
    implements(IReactorFDSet)


    def __init__(self):
        """
        Initialize kqueue object, file descriptor tracking dictionaries, and the
        base class.
        """
        self._kq = kqueue()
        self._reads = {}
        self._writes = {}
        self._selectables = {}
        posixbase.PosixReactorBase.__init__(self)


    def _updateRegistration(self, fd, filter, op):
        """
        Private method for changing kqueue registration.
        """
        self._kq.control([kevent(fd, filter, op)], 0, 0)


    def addReader(self, reader):
        """
        Add a FileDescriptor for notification of data available to read.
        """
        fd = reader.fileno()
        if fd not in self._reads:
            try:
                self._updateRegistration(fd, KQ_FILTER_READ, KQ_EV_ADD)
            except OSError, e:
                pass
            finally:
                self._selectables[fd] = reader
                self._reads[fd] = 1


    def addWriter(self, writer):
        """
        Add a FileDescriptor for notification of data available to write.
        """
        fd = writer.fileno()
        if fd not in self._writes:
            try:
                self._updateRegistration(fd, KQ_FILTER_WRITE, KQ_EV_ADD)
            except OSError, e:
                pass
            finally:
                self._selectables[fd] = writer
                self._writes[fd] = 1


    def removeReader(self, reader):
        """
        Remove a Selectable for notification of data available to read.
        """
        wasLost = False
        try:
            fd = reader.fileno()
        except:
            fd = -1
        if fd == -1:
            for fd, fdes in self._selectables.items():
                if reader is fdes:
                    wasLost = True
                    break
            else:
                return
        if fd in self._reads:
            del self._reads[fd]
            if fd not in self._writes:
                del self._selectables[fd]
            if not wasLost:
                try:
                    self._updateRegistration(fd, KQ_FILTER_READ, KQ_EV_DELETE)
                except OSError, e:
                    pass


    def removeWriter(self, writer):
        """
        Remove a Selectable for notification of data available to write.
        """
        wasLost = False
        try:
            fd = writer.fileno()
        except:
            fd = -1
        if fd == -1:
            for fd, fdes in self._selectables.items():
                if writer is fdes:
                    wasLost = True
                    break
            else:
                return
        if fd in self._writes:
            del self._writes[fd]
            if fd not in self._reads:
                del self._selectables[fd]
            if not wasLost:
                try:
                    self._updateRegistration(fd, KQ_FILTER_WRITE, KQ_EV_DELETE)
                except OSError, e:
                    pass


    def removeAll(self):
        """
        Remove all selectables, and return a list of them.
        """
        return self._removeAll(
            [self._selectables[fd] for fd in self._reads],
            [self._selectables[fd] for fd in self._writes])


    def getReaders(self):
        return [self._selectables[fd] for fd in self._reads]


    def getWriters(self):
        return [self._selectables[fd] for fd in self._writes]


    def doKEvent(self, timeout):
        """
        Poll the kqueue for new events.
        """
        if timeout is None:
            timeout = 1

        try:
            l = self._kq.control([], len(self._selectables), timeout)
        except OSError, e:
            if e[0] == errno.EINTR:
                return
            else:
                raise

        _drdw = self._doWriteOrRead
        for event in l:
            fd = event.ident
            try:
                selectable = self._selectables[fd]
            except KeyError:
                # Handles the infrequent case where one selectable's
                # handler disconnects another.
                continue
            else:
                log.callWithLogger(selectable, _drdw, selectable, fd, event)


    def _doWriteOrRead(self, selectable, fd, event):
        why = None
        inRead = False
        filter, flags, data, fflags = event.filter, event.flags, event.data, event.fflags

        if flags & KQ_EV_EOF and data and fflags:
            why = main.CONNECTION_LOST
        else:
            try:
                if selectable.fileno() == -1:
                    inRead = False
                    why = posixbase._NO_FILEDESC
                else:
                   if filter == KQ_FILTER_READ:
                       inRead = True
                       why = selectable.doRead()
                   if filter == KQ_FILTER_WRITE:
                       inRead = False
                       why = selectable.doWrite()
            except:
                # Any exception from application code gets logged and will
                # cause us to disconnect the selectable.
                why = sys.exc_info()[1]
                log.err()

        if why:
            self._disconnectSelectable(selectable, why, inRead)

    doIteration = doKEvent


def install():
    """
    Install the kqueue() reactor.
    """
    p = KQueueReactor()
    from twisted.internet.main import installReactor
    installReactor(p)


__all__ = ["KQueueReactor", "install"]
