##
## A test to check whether kqueue supports PTY file descriptors.
##
## On FreeBSD, kqueue can be used for PIPEs, and on MacOSX, that
## seems to be unsupported
##

import sys
from select import kqueue, kevent, KQ_FILTER_READ, KQ_EV_ADD, KQ_EV_ERROR

k = kqueue()

# Add read filter for STDIN and wait 0 secs for at most 1 event.
r = k.control([kevent(sys.stdin.fileno(), KQ_FILTER_READ, KQ_EV_ADD)], 1, 0)

print r

if len(r) == 0:
   print "kqueue seems to support PTY"
else:
   if r[0].flags & KQ_EV_ERROR:
      print "kqueue has no support for PTY"
   else:
      ## above 2 cases seem to be sufficient to distinguish at least
      ## between FreeBSD and MacOSX .. so we're lazy
      print "don't know whether kqueue supports PTY or not"
