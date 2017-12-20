#!/usr/bin/env python

"""
.. _build_patch_lists:

Build the list of patches
=========================
"""


from __future__ import print_function
import os
import subprocess
from optparse import OptionParser


__author__ = 'Nicolas Chotard <nchotard@in2p3.fr>'
__version__ = '$Revision: 1.0 $'


def build_config(config):
    """
    Build the needed configuration file to run makeSkyMap.py
    """
    f = open(config, 'w')
    f.write("""config.skyMap.projection='TAN'

# dimensions of inner region of patches (x,y pixels)
config.skyMap.patchInnerDimensions=[4000, 4000]
    
# nominal pixel scale (arcsec/pixel) 
config.skyMap.pixelScale=0.185""")
    f.close()

if __name__ == "__main__":
    
    usage = """%prog [option]"""
    
    description = """This script will find the patches for all filters"""
    
    parser = OptionParser(description=description, usage=usage)
    parser.add_option("-f", "--filters", type="string",
                      help="Filter(s) [%default]. Can also be a ist of filter ('ugriz')")
    parser.add_option("-c", "--config", type="string", default="makeSkyMapConfig.py",
                      help="If not given or present in the local dir, a standard one will be created.")
    parser.add_option("--input", type="string", default='pardir/output',
                      help='input directory [%default]')
    parser.add_option("--output", type="string", default='pardir/output',
                      help='output directory [%default]')
    opts, args = parser.parse_args()

    if not os.path.exists(opts.config):
        print("WARNING: The given (or default) configuration file does not exists.")
        print("INFO: Building a new configuration file")
        build_config(opts.config)

    opts.filters = opts.filters.split(",")

    # Create a file containing the list of all visits
    cmd = "cat [%s].list > all.list" % "\|".join(opts.filters)
    os.system(cmd)

    print("INFO: Running all commands for all visits")
    # makeSkyMap command
    cmd = "makeSkyMap.py %s --output %s --configfile %s" % \
          (opts.input, opts.output, opts.config)
    print("RUNNING:", cmd)
    subprocess.call(cmd, shell=True)

    cmd = 'reportPatchesWithImages.py %s --visits all.list | grep "^tract" > patches.txt' % \
          (opts.output)
    print("RUNNING:", cmd)
    subprocess.call(cmd, shell=True)

    # Check the input filter
    for filt in opts.filters:
        cmd = "sed -e 's/^/--id filter=%s /' patches.txt > patches_%s.txt" % (filt, filt)
        print("\nRUNNING:", cmd)
        subprocess.call(cmd, shell=True)

    cmd = "sed -e 's/^/--id filter=%s /' patches.txt > patches_all.txt" % ("^".join(opts.filters))
    print("\nRUNNING:", cmd)
    subprocess.call(cmd, shell=True)
    print("INFO: End of run")