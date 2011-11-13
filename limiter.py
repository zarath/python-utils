#!/usr/bin/env python
"""limiter.py 

Provides checking if something was called multiple times in a
given timeframe.

Usage:
    -h, --help
    -q, --quiet
    -f, --file
    -m, --max
    -t, --nseconds
    [-l, --logfile]

Example:

./limiter.py -f /tmp/limit -l /tmp/limit.log -m 1 -t 10 -q "Comment" && echo "OK"

Copyright 2011 Holger Mueller 

    This program is free software: you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public License
    as published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this program. If not, see
    <http://www.gnu.org/licenses/>.

"""

import time
from fcntl import flock, LOCK_EX, LOCK_UN
import bsddb

class Limiter:
    def __init__(self, dbpath, log=None):
    	self.db = dbpath + ".db"
    	self.lck = dbpath + ".lck"
    	self.lckfd = None
    	self.tstamp = time.time()
	
    	if log:
    	    self.logfile = open(log, "a")
    	else:
    	    self.logfile = None
    
    def lock(self):
    	self.tstamp = time.time()
    	self.lckfd = open(self.lck, "w")
    	flock(self.lckfd, LOCK_EX)
    
    def unlock(self):
    	flock(self.lckfd, LOCK_UN)
    	self.lckfd.close()

    def insert(self, entry):
    	self.tstamp = time.time()
    	log = bsddb.btopen(self.db)
    	log["%10.6f" % time.time()] = entry
    	log.sync()
    	log.close()
    
    def last(self, count=1):
    	ret = []
    	if count == 0:
    	    return ret

    	try:	
    	    log = bsddb.btopen(self.db, "r")
    	except bsddb.db.DBNoSuchFileError:
    	    return ret
    	
    	try:
    	    ret.append(log.last())
    	except bsddb.error:
    	    return ret
    	
    	i = 1
    	while i < count:
    	    i += 1
    	    try:
                ret.append(log.previous())
    	    except bsddb.error:
                return ret
    
    	return ret

    def maxpernseconds(self, max, nseconds):
        """checks if no more then max calls per nseconds"""
    
    	now = time.time()
    	 
    	recent = self.last(max)
    
    	if len(recent) < max:
    	    return False
    	
    	if now - float(recent[-1][0]) > nseconds:
    	    return False
    	
    	return True

    def log(self, entry, timestamp=None):
    	try:
    	    if not timestamp:
                self.logfile.write("%10.6f: " % self.tstamp)
    	    else:
                self.logfile.write("%10.6f: " % timestamp)
                self.logfile.write(entry)
                self.logfile.write("\n")
                self.logfile.flush()
    	except:
    	    pass

def limit(dbpath, entry="", max=3, nseconds=900, log=None):
    """
    Check if this functions was called in the limits of given parameters
    
    @type dbpath: filename
    @param dbpath: The filename of the locking an db file without an extension
    @type entry: string
    @param entry: an optional log entry
    @type max: int
    @param max: maximum amount of calls
    @type nseconds int
    @param nseconds: time limit
    @type log: filename
    @param log: optional logfile where each call to limit will be logged
    
    @rtype: boolean
    @return: True if calls are in limit 
    """

    limit = False
    l = Limiter(dbpath, log)
    l.lock()
    if not l.maxpernseconds(max, nseconds):
    	l.insert(entry)
    	limit = True
    l.unlock()
    if log:
    	if limit:
    	    l.log("OK - " + entry)
    	else:
    	    l.log("Error - " + entry)
    return limit

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    dbpath, entry, max, nseconds, log, quiet  = (None, "", 3, 900, None, False)
    
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "hf:m:t:l:q",
                                       ["help", "file=", "max=", "nseconds=",
                                        "logfile=", "quiet"])
        except getopt.error, msg:
             raise Usage(msg)

        for o, a in opts:
            if o in ("-h", "--help"):
            	print __doc__
            	sys.exit(0)
            if o in ("-f", "--file"):
                dbpath = a
            if o in ("-m", "--max"):
                max = int(a)
            if o in ("-t", "--nseconds"):
                nseconds = int(a)
            if o in ("-l", "--logfile"):
                log = a
            if o in ("-q", "--quiet"):
                quiet = True

        entry = "".join(args)

        ret = limit(dbpath, entry, max, nseconds, log)
	
    	if ret:
    	    if not quiet: print "OK"
    	    return 0
    	else:
    	    if not quiet: print "Error"
    	    return 1

    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

    except TypeError:
	print __doc__
	sys.exit(0)
    
if __name__ == "__main__":
    import sys
    import getopt
    sys.exit(main())
