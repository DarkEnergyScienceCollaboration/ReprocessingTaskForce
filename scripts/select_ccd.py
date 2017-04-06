#!/usr/bin/env python

"""
.. _select_ccd:

Check the wcs scatter
=====================
"""

import os
import numpy as N
import pylab as P
from glob import glob
import seaborn
from ToolBox import Statistics
from optparse import OptionParser

__author__ = 'Nicolas Chotard <nchotard@in2p3.fr>'
__version__ = '$Revision: 1.0 $'

RERUN = []

def read_log(log):
    complete_log = False
    f = open(log, 'r')
    d = {}
    for l in f:
        if l.startswith("processCcd: Processing"):
            sd = eval(l.split("processCcd: Processing ")[1])
            if not len(d):
                d[sd['visit']] = {}
            d[sd['visit']][sd['ccd']] = sd
        if l.startswith("processCcd.calibrate.astrometry: Matched and fit WCS"):
            ll=l.split()
            ast={'iterations': ll[6], 'matches': ll[9],
                'scatter': ll[14], 'scatter_sgm': ll[16], 'unit': ll[17]}
            d[sd['visit']][sd['ccd']].update(ast)
            if float(ast['scatter']) == 0:
                print "WARNING: WSC scatter is 0 for visit %s, ccd %s" % (sd['visit'], sd['ccd'])
        elif l.startswith("processCcd.calibrate.astrometry: Astrometric scatter"):
            ll=l.split()
            ast={'matches': ll[8], 'scatter': ll[3], 'unit': ll[4], 'rejected': ll[10]}
            d[sd['visit']][sd['ccd']].update(ast)
        if l.startswith("*   maxvmem:"):
            complete_log = True
    if not complete_log:
        print "WARNING: The following log is not complete:", log
        RERUN.append(". %s" % log.replace("log/", "scripts/").replace('.log', '.sh'))
    return d

def get_logs(logdir, filt):
    logs = glob(logdir+'/%s/*.log' % filt)
    d = {}
    for log in sorted(logs):
        d.update(read_log(log))
    return d

def create_list(f, d, r):
    ff = open("%s.list" % f, 'w')
    for v in sorted(d[f]):
        ccd = "^".join(str(i) for i in range(36) if i not in r[f][v])
        ff.write("--selectId visit=%i ccd=%s\n" % (v, ccd))
    ff.close()
    
if __name__ == "__main__":


    parser = OptionParser()
    parser.add_option("-l", "--logdir", type="string", help="Log directory")
    parser.add_option("-f", "--filters", type="string", help="Filter set [%default]", default="ugriz")
    parser.add_option("-r", "--scatter_range", type="string",
                      help="The scatter range to keep [%default]", default="0.02,0.1")
    opts, args = parser.parse_args()

    min_scatter, max_scatter = map(float, opts.scatter_range.split(','))
    
    # Read the logs, get the data
    d = {f: get_logs(opts.logdir, f) for f in opts.filters}
    rejected = {f: {v: [] for v in d[f]} for f in opts.filters}
    for f in opts.filters:
        ii = 0
        for v in sorted(d[f]):
            for ccd in sorted(d[f][v]):
                if 'scatter' in d[f][v][ccd]:
                    scatter = float(d[f][v][ccd]['scatter'])
                    if scatter < min_scatter or scatter > max_scatter:
                        print "Scatter < %.2f or > %.2f for " % (min_scatter, max_scatter), \
                            f, v, ccd, scatter
                        rejected[f][v].append(int(ccd))
                        ii += 1
                else:
                    print "No scatter for", f, v, ccd
                    rejected[f][v].append(int(ccd))
                    ii += 1
        create_list(f, d, rejected)
        print ii, "/ %i CCDs rejected for filter %s" % (sum([36*len(d[f])]), f)
        