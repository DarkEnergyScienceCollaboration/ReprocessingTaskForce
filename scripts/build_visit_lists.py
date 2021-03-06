#!/usr/bin/env python

"""
.. _build_visit_lists:

Build the list of visit for a given cluster
===========================================
"""


from __future__ import print_function
import os
import glob
from optparse import OptionParser
import lsst.daf.persistence as dafPersist


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
            if sd['visit'] not in d:
                d[sd['visit']] = {}
            d[sd['visit']][sd['ccd']] = sd
        if l.startswith("processCcd.calibrate.astrometry: Matched and fit WCS"):
            ll=l.split()
            ast={'iterations': ll[6], 'matches': ll[9],
                'scatter': ll[14], 'scatter_sgm': ll[16], 'unit': ll[17]}
            d[sd['visit']][sd['ccd']].update(ast)
            if float(ast['scatter']) == 0:
                print("WARNING: WSC scatter is 0 for visit %s, ccd %s" % (sd['visit'], sd['ccd']))
        elif l.startswith("processCcd.calibrate.astrometry: Astrometric scatter"):
            ll=l.split()
            ast={'matches': ll[8], 'scatter': ll[3], 'unit': ll[4], 'rejected': ll[10]}
            d[sd['visit']][sd['ccd']].update(ast)
        if l.startswith("*   maxvmem:"):
            complete_log = True
    f.close()
    if not complete_log:
        print("WARNING: The following log is not complete:", log)
        RERUN.append(". %s" % log.replace("log/", "scripts/").replace('.log', '.sh'))
    return d

def get_logs(logs):
    loglist = []
    for l in logs.split(','):
        loglist.extend(glob.glob(l))
    print("INFO: %i logs loaded" % len(loglist))
    d = {}
    for i, log in enumerate(loglist):
        ld = read_log(log)
        for v in ld:
            if v in d:
                d[v].update(ld[v])
            else:
                d[v] = ld[v]
    return d

def create_list(f, d, r):
    ff = open("%s.list" % f, 'w')
    for v in sorted(d[f]):
        ccd = "^".join(str(i) for i in range(36) if i not in r[f][v])
        ff.write("--selectId visit=%i ccd=%s\n" % (v, ccd))
    ff.close()

if __name__ == "__main__":

    description = "Build the list of visit for a given cluster for all available filters"
    usage = """usage: %prog [options] datadir

    datadir: absolute path to the directory containing the calibrated data (.fits.fz)"""

    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-i", "--input", help="Directory conting the input fits files.")
    parser.add_option("--idopt", help="id option to put in fron of the visit "
                      "name. Could be 'selectId' or 'id' [%default]",
                      default='id', type='string')
    parser.add_option("-l", "--logs", type="string", help="Logs select ccd (coma separated for "
                      "several logs, or \*.log for multiple log in the same dir.")
    parser.add_option("-r", "--scatter_range", type="string", default="0.02,0.1",
                      help="Astrometric scatter range in which a ccd has to be [%default]")
    parser.add_option("-x", "--exclude", type="string",
                      help="List of visit/ccd to exclude. Format is the same as in the output file"
                      ", e.g visit=850760 ccd=11^16")
    options, args = parser.parse_args()

    if options.input is None:
        raise IOError("Please use the input option")
    if not os.path.exists(options.input):
        raise IOError("Input directory does not exists")
    if not options.input.endswith('/'):
        options.input += '/'
    if options.idopt not in ['selectId', 'id']:
        raise IOError("Option idopt must be 'selectid' or 'id'")

    # Load the butler for this input directory
    butler = dafPersist.Butler(options.input)

    # The catalog we want correspond to the raw data
    catalog = 'raw'

    # Get all keys available in a dataId dictionary for this catalog
    keys = butler.getKeys(catalog)

    # Construct fthe dataIds dictionnary for all available data
    metadata = butler.queryMetadata(catalog, format=sorted(keys.keys()))
    dataids = [dict(zip(sorted(keys.keys()), list(v) if not isinstance(v, list) else v))
               for v in metadata]

    # Get the list of available filters
    filters = set([dataid['filter'] for dataid in dataids])

    # Dictionnary of visits per filter
    visits = {filt: list(set([dataid['visit'] for dataid in dataids if dataid['filter'] == filt]))
              for filt in filters}

    # Print some info
    print("The total number of visits is", sum([len(visits[filt]) for filt in visits]))
    print("The number of visits per filter are:")
    for filt in sorted(visits):
        print(" - %s: %i" % (filt, len(visits[filt])))

    # Do we select CCD based on the astrometric scatter?
    if options.logs is not None:
        ii = 0
        min_scatter, max_scatter = map(float, options.scatter_range.split(','))
        logs = get_logs(options.logs) # Read the logs, get the data
        d = {f: {} for f in filters} # orgize the visit per filter
        for v in logs:
            f = logs[v][logs[v].keys()[0]]['filter']
            d[f][v] = logs[v]
        rejected = {f: {int(v): [] for v in visits[f]} for f in filters}
        for f in filters:
            for v in sorted(d[f]):
                for ccd in sorted(d[f][v]):
                    if 'scatter' in d[f][v][ccd]:
                        scatter = float(d[f][v][ccd]['scatter'])
                        if scatter < min_scatter or scatter > max_scatter:
                            print("Scatter < %.2f or > %.2f for " % (min_scatter, max_scatter), \
                                f, v, ccd, scatter)
                            rejected[f][v].append(int(ccd))
                    else:
                        print("No astrometric scatter (processCcd crashed) for", f, v, ccd)
                        rejected[f][v].append(int(ccd))
                        ii += 1
            print(sum([len(rejected[f][v]) for v in rejected[f]]), \
                "/ %i CCDs rejected for filter %s (actually %i ccds)\n" % \
                (sum([36*len(d[f])]), f, sum([len(d[f][v]) for v in d[f]])))
    else:
        rejected = None

    # Do we have an input exlcude list?
    exclude = {v: [] for f in visits for v in visits[f]}
    if options.exclude is not None:
        el = N.loadtxt(options.exclude, dtype='str', unpack=True)
        for v, ccds in zip(el[0], el[1]):
            exclude[v.split('=')[1]] = ccds.split('=')[1].split('^')

    # Write and save the list, including the ccd selection if needed
    print("Wrinting visit list in separated files for each filter")        
    for f in visits:
        vf = "%s.list" % f
        ff = open(vf, 'w')
        for v in visits[f]:
            if rejected is not None:
                ccd = "^".join(str(i) for i in range(36) if i not in rejected[f][int(v)]
                               and str(i) not in exclude[v])
            else:
                ccd = "^".join(str(i) for i in range(36) if str(i) not in exclude[v])
            if len(ccd):
                ff.write("--%s visit=%s ccd=%s\n" % (options.idopt, v, ccd))
            else:
                ff.write("--%s visit=%s\n" % (options.idopt, v))
        ff.close()
        print(" - %s: %i visits -> %s" %(f, len(visits[f]), vf))
