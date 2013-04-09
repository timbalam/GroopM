#!/usr/bin/env python
###############################################################################
#                                                                             #
#    groopm.py                                                                #
#                                                                             #
#    Wraps coarse workflows                                                   #
#                                                                             #
#    Copyright (C) Michael Imelfort                                           #
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

__author__ = "Michael Imelfort"
__copyright__ = "Copyright 2012"
__credits__ = ["Michael Imelfort"]
__license__ = "GPL3"
__version__ = "0.2.1"
__maintainer__ = "Michael Imelfort"
__email__ = "mike@mikeimelfort.com"
__status__ = "Alpha"

###############################################################################

import argparse
import sys
import os 

# GroopM imports
import mstore
import cluster
import refine
import bin
import binManager
import groopmUtils
import groopmTimekeeper as gtime

###############################################################################
###############################################################################
###############################################################################
###############################################################################
# Track rogue print statements
#from groopmExceptions import Tracer
#sys.stdout = Tracer(sys.stdout)
#sys.stderr = Tracer(sys.stderr)
###############################################################################
###############################################################################
###############################################################################
###############################################################################

class GroopMOptionsParser():
    def __init__(self): pass
    
    def parseOptions(self, options ):

        timer = gtime.TimeKeeper()
        if(options.subparser_name == 'parse'):
            # parse raw input
            print "*******************************************************************************"
            print " [[GroopM]] Running in data parsing mode..."
            print "*******************************************************************************"
            GMdata = mstore.GMDataManager()
            success = GMdata.createDB(options.bamfiles,
                                      options.reference,
                                      options.dbname,
                                      timer,
                                      dumpAll=options.dump,
                                      force=options.force)
            if not success:
                print options.dbname,"not updated" 
                            
        elif(options.subparser_name == 'core'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in core creation mode..."
            print "*******************************************************************************"
            CE = cluster.ClusterEngine(options.dbname,
                                       force=options.force,
                                       finalPlot=options.plot,
                                       plot=options.multiplot,
                                       minSize=options.size,
                                       minVol=options.bp
                                       )
            if options.graphfile is None:
                gf = ""
            else:
                gf=options.graphfile
            CE.makeCores(timer,
                         coreCut=options.cutoff,
                         gf=gf)

        elif(options.subparser_name == 'refine'):
            # refine bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in core refining mode..."
            print "*******************************************************************************"
            bids = []
            if options.bids is not None:
                bids = options.bids            
            auto = options.auto
            transform=True^options.no_transform
            
            RE = refine.RefineEngine(timer,
                                     dbFileName=options.dbname,
                                     transform=transform,
                                     bids=bids)
            if options.plot:
                pfx="REFINED"
            else:
                pfx=""
            print "Refine bins"
            
            RE.refineBins(timer,
                          auto=auto,
                          saveBins=True,
                          plotFinal=pfx)

        elif(options.subparser_name == 'recruit'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin expansion mode..."
            print "*******************************************************************************"
            RE = refine.RefineEngine(timer,
                                     dbFileName=options.dbname,
                                     getUnbinned=True,
                                     loadContigNames=False
                                     )

            RE.recruitWrapper(timer,
                              inclusivity=options.inclusivity,
                              step=options.step,
                              saveBins=True)
        
        elif(options.subparser_name == 'extract'):
            # Extract data
            print "*******************************************************************************"
            print " [[GroopM]] Running in '%s' extraction mode..." % options.mode 
            print "*******************************************************************************"
            bids = []
            if options.bids is not None:
                bids = options.bids
            BX = groopmUtils.GMExtractor(options.dbname,
                                          bids=bids,
                                          folder=options.outfolder
                                          )
            if(options.mode=='contigs'):
                BX.extractContigs(timer, fasta=options.data, cutoff=options.cutoff)
            elif(options.mode=='reads'):
                BX.extractReads(timer, bams=options.data)
            else:
                raise ge.ExtractModeNotAppropriateException("mode: "+mode+" is unknown")

        elif(options.subparser_name == 'merge'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin merging mode..."
            print "*******************************************************************************"
            BM = binManager.BinManager(dbFileName=options.dbname)
            BM.loadBins(timer, makeBins=True, silent=False)
            BM.merge(options.bids, options.force, saveBins=True)

        elif(options.subparser_name == 'split'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin splitting mode..."
            print "*******************************************************************************"
            BM = binManager.BinManager(dbFileName=options.dbname)
            BM.loadBins(timer, makeBins=True, silent=False)
            BM.split(options.bid, options.parts, mode=options.mode, saveBins=True, auto=options.force)

        elif(options.subparser_name == 'delete'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin deleting mode..."
            print "*******************************************************************************"
            BM = binManager.BinManager(dbFileName=options.dbname)
            BM.loadBins(timer, makeBins=True, silent=True, bids=options.bids)
            BM.deleteBins(options.bids, force=options.force, saveBins=True, freeBinnedRowIndices=True)

        elif(options.subparser_name == 'explore'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin '%s' explorer mode..." % options.mode
            print "*******************************************************************************"
            bids = []
            if options.bids is not None:
                bids = options.bids
            BE = groopmUtils.BinExplorer(options.dbname, bids=bids)
            if(options.mode == 'points'):
                BE.plotPoints(timer)
            elif(options.mode == 'contigs'):
                BE.plotContigs(timer)
            elif(options.mode == 'ids'):
                BE.plotIds(timer)
            elif(options.mode == 'flyover'):
                BE.plotFlyOver(timer)
            elif(options.mode == 'profile'):
                BE.plotBinProfiles(timer)
            elif(options.mode == 'compare'):
                BE.plotSideBySide(timer, coreCut=options.cutoff)
            elif(options.mode == 'unbinned'):
                BE.plotUnbinned(timer, coreCut=options.cutoff)
            else:
                print "**Error: unknown mode:",options.mode

        elif(options.subparser_name == 'highlight'):
            # make bin cores
            print "*******************************************************************************"
            print " [[GroopM]] Running in highlighter mode..."
            print "*******************************************************************************"
            BE = groopmUtils.BinExplorer(options.dbname, bids=[])
            BE.plotHighlights(timer,
                              options.bids,
                              options.elevation,
                              options.azimuth,
                              options.file,
                              options.filetype,
                              options.dpi,
                              options.alpha,
                              options.invert)
            
        elif(options.subparser_name == 'print'):
            BM = binManager.BinManager(dbFileName=options.dbname)
            bids = []
            if options.bids is not None:
                bids = options.bids
            BM.loadBins(timer, getUnbinned=options.unbinned, makeBins=True, silent=True, bids=bids)
            BM.printBins(options.format, fileName=options.outfile)

        elif(options.subparser_name == 'plot'):
            print "*******************************************************************************"
            print " [[GroopM]] Running in bin plotting mode..."
            print "*******************************************************************************"
            BM = binManager.BinManager(dbFileName=options.dbname)
            if options.bids is None:
                bids = []
            else:    
                bids = options.bids
            BM.loadBins(timer, makeBins=True, silent=False, bids=bids, loadContigNames=False)

            if options.bids is None:
                bids = BM.getBids()

            if options.together:
                BM.plotSelectBins(bids,
                                  plotMers=options.kmers,
                                  plotEllipsoid=True)
            else:
                BM.plotBins(FNPrefix=options.tag,
                            sideBySide=options.sidebyside,
                            plotEllipsoid=True,
                            folder=options.folder)
        return 0
    

###############################################################################
###############################################################################
###############################################################################
###############################################################################
