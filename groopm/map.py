#!/usr/bin/env python
###############################################################################
#                                                                             #
#    map.py                                                                   #
#                                                                             #
#    A collection of classes for finding marker genes                         #
#                                                                             #
#    Copyright (C) Tim Lamberton                                              #
#                                                                             #
###############################################################################
#                                                                             #
#          .d8888b.                                    888b     d888          #
#         d88P  Y88b                                   8888b   d8888          #
#         888    888                                   88888b.d88888          #
#         888        888d888 .d88b.   .d88b.  88888b.  888Y88888P888          #
#         888  88888 888P"  d88""88b d88""88b 888 "88b 888 Y888P 888          #
#         888    888 888    888  888 888  888 888  888 888  Y8P  888          #
#         Y88b  d88P 888    Y88..88P Y88..88P 888 d88P 888   "   888          #
#          "Y8888P88 888     "Y88P"   "Y88P"  88888P"  888       888          #
#                                             888                             #
#                                             888                             #
#                                             888                             #
#                                                                             #
###############################################################################
#                                                                             #
#    This program is free software: you can redistribute it and/or modify     #
#    it under the terms of the GNU General Public License as published by     #
#    the Free Software Foundation, either version 3 of the License, or        #
#    (at your option) any later version.                                      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program. If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

__author__ = "Tim Lamberton"
__copyright__ = "Copyright 2016"
__credits__ = ["Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "t.lamberton@uq.edu.au"

###############################################################################

import numpy as np
import os
import sys
import subprocess
from utils import CSVReader

###############################################################################
###############################################################################
###############################################################################
###############################################################################

class SingleMMapper:
    '''Class to find marker gene hits with SingleM
    '''
    
    def __init__(self, workingDir, force=False, silent=False):
        self.workingDir = workingDir
        self.force = force
        self.silent = silent
        self.errorOutput = ''
        if self.silent:
            self.errorOutput = '2> /dev/null'
        
    def getMappings(self, contig_file):
        otu_file = os.path.join(self.workingDir, 'singlem_otu_table.csv')
        cmd = ' '.join(['singlem pipe --sequences',
                        contig_file,
                        '--otu_table',
                        otu_file,
                        '--output_extras',
                        self.errorOutput])
        subprocess.check_call(cmd, shell=True)
        
        con_names = []
        map_markers = []
        map_taxstrings = []
        try:
            with open(otu_file, 'r') as fh:
                for l in self.readOtuTable(fh):
                    con_names.append(l[0])
                    map_markers.append(l[1])
                    try:
                        map_taxstrings.append(l[2])
                    except IndexError:
                        map_taxstrings.append("")
        except:
            print "Error when reading SingleM otu table", sys.exc_info()[0]
            raise
            
        return (con_names, map_markers, map_taxstrings)
        
    def readOtuTable(self, otu_file):
        """Parse singleM otu table"""
        reader = CSVReader()
        cols = None
        for l in reader.readCSV(otu_file, "\t"):
            if cols is None:
                cols_lookup = dict(zip(l, range(len(l))))
                cols = [cols_lookup['read_names'], cols_lookup['gene']]
                try:
                    cols += [cols_lookup['taxonomy']]
                except KeyError:
                    pass
                continue
            yield tuple(l[i] for i in cols)

            
class GraftMMapper:
    """Class to find marker gene hits for a set of GraftM packages"""
    
    def __init__(self, workingDir, packageList, silent=False, force=False):
        self.workingDir = workingDir
        self.packageList = packageList
        self.silent = silent
        self.force = force
        
        self.errorOutput = ''
        if self.silent:
            self.errorOutput = '2> /dev/null'
            
    def getMappings(self, contigFile):
        read_tax_files = {}
        for (name, package) in self.packageList.iteritems():
            read_tax_files[name] = self.mapPackage(contigFile, name, package)
        
        con_names = []
        map_markers = []
        map_taxstrings = []
        for (name, filename) in read_tax_files.iteritems():
            try:
                with open(filename, 'r') as fh:
                    for (cname, taxstring) in self.readTaxTable(fh):
                        con_names.append(cname)
                        map_markers.append(name)
                        map_taxstrings.append(taxstring)
            except:
                print "Error when reading GraftM taxonomy assigned using package: ", name, sys.exc_info()[0]
                raise
                
        return (con_names, map_markers, map_taxstrings)
        
    def mapPackage(self, contigFile, package_name, package):
        basename = os.path.basename(contigFile)
        prefix = None
        for ext in [ '.fa', '.fna', '.fasta', '.fa.gz', '.fna.gz', '.fasta.gz']:
            if basename.endswith(ext):
                prefix = basename[:len(basename)-len(ext)]
                break
        if prefix is None:
            raise ValueError("Not a compatible extension {.fa[.gz]|.fna[.gz]|.fasta[.gz]} using contigs file: %s" % contigsFile)
        output_dir = os.path.join(self.workingDir, "%s_%s" % (prefix, package_name))
        cmd = ' '.join(['graftM graft --forward',
                        contigFile,
                        '--graftm_package',
                        package,
                        '--output_directory',
                        output_dir,
                        '--verbosity 2',
                        self.errorOutput])
        subprocess.check_call(cmd, shell=True)
        return os.path.join(output_dir, prefix, "%s_read_tax.tsv" % prefix)
        
        
    def readTaxTable(self, otu_file):
        """Parse graftm taxonomy table"""
        
        reader = CSVReader()
        for (cname, taxstring) in reader.readCSV(otu_file, "\t"):
            # strip _(num)_(num)_(num) suffix
            parsed = cname
            for _ in range(3):
                parsed = parsed.rstrip('1234567890')
                if not parsed.endswith('_') or len(parsed) < 2:
                    raise ValueError('Error encountered when parsing contig name: %s' % cname)
                parsed = parsed[:-1]
            yield (parsed, taxstring)
        
        
        
            
###############################################################################
###############################################################################
###############################################################################
###############################################################################
