#!/usr/bin/env python
###############################################################################
#                                                                             #
#    profileManager.py                                                          #
#                                                                             #
#    GroopM - High level data management                                      #
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

from sys import exc_info, exit, stdout as sys_stdout
from operator import itemgetter
from colorsys import hsv_to_rgb as htr
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d, Axes3D
from pylab import plot,subplot,axis,stem,show,figure
from numpy import (abs as np_abs,
                   amax as np_amax,
                   amin as np_amin,
                   append as np_append,
                   arange as np_arange,
                   arccos as np_arccos,
                   argmin as np_argmin,
                   argsort as np_argsort,
                   array as np_array,
                   ceil as np_ceil,
                   concatenate as np_concatenate,
                   copy as np_copy,
                   cos as np_cos,
                   delete as np_delete,
                   diag as np_diag,
                   eye as np_eye,
                   log10 as np_log10,
                   max as np_max,
                   mean as np_mean,
                   median as np_median,
                   min as np_min,
                   pi as np_pi,
                   reshape as np_reshape,
                   seterr as np_seterr,
                   shape as np_shape,
                   sin as np_sin,
                   size as np_size,
                   sort as np_sort,
                   sqrt as np_sqrt,
                   std as np_std,
                   transpose as np_transpose,
                   where as np_where,
                   zeros as np_zeros)
from numpy.linalg import norm as np_norm
#import scipy.ndimage as ndi
from scipy.spatial.distance import cdist, squareform
from scipy.spatial import KDTree as kdt
from scipy.stats import f_oneway, distributions

# GroopM imports
from PCA import PCA, Center
from mstore import GMDataManager
from bin import Bin
import groopmExceptions as ge

np_seterr(all='raise')

###############################################################################
###############################################################################
###############################################################################
###############################################################################

class ProfileManager:
    """Interacts with the groopm DataManager and local data fields

    Mostly a wrapper around a group of numpy arrays and a pytables quagmire
    """
    def __init__(self, dbFileName, force=False, scaleFactor=1000, squish=False):
        # data
        self.dataManager = GMDataManager()  # most data is saved to hdf
        self.dbFileName = dbFileName        # db containing all the data we'd like to use
        self.condition = ""                 # condition will be supplied at loading time
        # --> NOTE: ALL of the arrays in this section are in sync
        # --> each one holds information for an individual contig
        self.indices = np_array([])        # indices into the data structure based on condition
        self.covProfiles = np_array([])     # coverage based coordinates
        self.transformedCP = np_array([])   # the munged data points
        self.corners = np_array([])         # the corners of the tranformed space
        self.averageCoverages = np_array([]) # average coverage across all stoits
        self.normCoverages = np_array([])   # norm of the raw coverage vectors
        self.kmerSigs = np_array([])        # raw kmer signatures
        self.kmerNormPC1 = np_array([])     # First PC of kmer sigs normalized to [0, 1]
        self.kmerPCs = np_array([])         # PCs of kmer sigs capturing specified variance
        self.stoitColNames = np_array([])
        self.contigNames = np_array([])
        self.contigLengths = np_array([])
        self.contigGCs = np_array([])
        self.contigColors = np_array([])   # calculated from kmerNormPC1

        self.binIds = np_array([])          # list of bin IDs
        # --> end section

        # meta
        self.validBinIds = {}               # valid bin ids -> numMembers
        self.binnedRowIndices = {}         # dictionary of those indices which belong to some bin
        self.restrictedRowIndices = {}     # dictionary of those indices which can not be binned yet
        self.numContigs = 0                 # this depends on the condition given
        self.numStoits = 0                  # this depends on the data which was parsed

        # contig links
        self.links = {}

        # misc
        self.forceWriting = force           # overwrite existng values silently?
        self.scaleFactor = scaleFactor      # scale every thing in the transformed data to this dimension
        self.squish = squish

    def loadData(self,
                 timer,
                 condition="",              # condition as set by another function
                 bids=[],                   # if this is set then only load those contigs with these bin ids
                 verbose=True,              # many to some output messages
                 silent=False,              # some to no output messages
                 loadCovProfiles=True,
                 loadKmerSigs=True,
                 loadRawKmers=False,
                 makeColors=True,
                 loadContigNames=True,
                 loadContigLengths=True,
                 loadContigGCs=True,
                 loadBins=False,
                 loadLinks=False):
        """Load pre-parsed data"""
        timer.getTimeStamp()
        if(silent):
            verbose=False
        if verbose:
            print "Loading data from:", self.dbFileName

        # check to see if we need to override the condition
        if(len(bids) != 0):
            condition = "((bid == "+str(bids[0])+")"
            for index in range (1,len(bids)):
                condition += " | (bid == "+str(bids[index])+")"
            condition += ")"
        try:
            self.numStoits = self.getNumStoits()
            self.condition = condition
            self.indices = self.dataManager.getConditionalIndices(self.dbFileName,
                                                                  condition=condition,
                                                                  silent=silent)
            if(verbose):
                print "    Loaded indices with condition:", condition
            self.numContigs = len(self.indices)

            if self.numContigs == 0:
                print "    ERROR: No contigs loaded using condition:", condition
                return

            if(not silent):
                print "    Working with: %d contigs" % self.numContigs

            if(loadCovProfiles):
                if(verbose):
                    print "    Loading coverage profiles"
                self.covProfiles = self.dataManager.getCoverageProfiles(self.dbFileName, indices=self.indices)
                self.normCoverages = np_array([np_norm(self.covProfiles[i]) for i in range(len(self.indices))])

                # work out average coverages
                self.averageCoverages = np_array([sum(i)/self.numStoits for i in self.covProfiles])

            if loadRawKmers:
                if(verbose):
                    print "    Loading RAW kmer sigs"
                self.kmerSigs = self.dataManager.getKmerSigs(self.dbFileName, indices=self.indices)

            if(loadKmerSigs):
                PCs = self.dataManager.getKmerPCAs(self.dbFileName, indices=self.indices)
                self.kmerPCs = PCs

                if(verbose):
                    print "    Loading PCA kmer sigs (" + str(len(self.kmerPCs[0])) + " dimensional space)"

                self.kmerNormPC1 = PCs[:,0]
                self.kmerNormPC1 -= np_min(self.kmerNormPC1)
                self.kmerNormPC1 /= np_max(self.kmerNormPC1)

                if(makeColors):
                    if(verbose):
                        print "    Creating color profiles"

                    # use HSV to RGB to generate colors
                    S = 1       # SAT and VAL remain fixed at 1. Reduce to make
                    V = 1       # Pastels if that's your preference...
                    self.contigColors = np_array([htr(val, S, V) for val in self.kmerNormPC1])

            if(loadContigNames):
                if(verbose):
                    print "    Loading contig names"
                self.contigNames = self.dataManager.getContigNames(self.dbFileName, indices=self.indices)

            if(loadContigLengths):
                self.contigLengths = self.dataManager.getContigLengths(self.dbFileName, indices=self.indices)
                if(verbose):
                    print "    Loading contig lengths (Total: %d BP)" % ( sum(self.contigLengths) )

            if(loadContigLengths):
                self.contigGCs = self.dataManager.getContigGCs(self.dbFileName, indices=self.indices)
                if(verbose):
                    print "    Loading contig GC ratios (Average GC: %0.3f)" % ( np_mean(self.contigGCs) )

            if(loadBins):
                if(verbose):
                    print "    Loading bin assignments"
                self.binIds = self.dataManager.getBins(self.dbFileName, indices=self.indices)
                if len(bids) != 0: # need to make sure we're not restricted in terms of bins
                    tmp_bids = self.getBinStats()
                    for bid in bids:
                        self.validBinIds[bid] = tmp_bids[bid]
                else:
                    self.validBinIds = self.getBinStats()

                # fix the binned indices
                self.binnedRowIndices = {}
                for i in range(len(self.indices)):
                    if(self.binIds[i] != 0):
                        self.binnedRowIndices[i] = True
            else:
                # we need zeros as bin indicies then...
                self.binIds = np_zeros(len(self.indices))

            if(loadLinks):
                self.loadLinks()

            self.stoitColNames = self.getStoitColNames()

        except:
            print "Error loading DB:", self.dbFileName, exc_info()[0]
            raise

    def reduceIndices(self, deadRowIndices):
        """purge indices from the data structures

        Be sure that deadRowIndices are sorted ascending
        """
        # strip out the other values
        self.indices = np_delete(self.indices, deadRowIndices, axis=0)
        self.covProfiles = np_delete(self.covProfiles, deadRowIndices, axis=0)
        self.transformedCP = np_delete(self.transformedCP, deadRowIndices, axis=0)
        self.contigNames = np_delete(self.contigNames, deadRowIndices, axis=0)
        self.contigLengths = np_delete(self.contigLengths, deadRowIndices, axis=0)
        self.contigColors = np_delete(self.contigColors, deadRowIndices, axis=0)
        #self.kmerSigs = np_delete(self.kmerSigs, deadRowIndices, axis=0)
        self.kmerPCs = np_delete(self.kmerPCs, deadRowIndices, axis=0)
        self.binIds = np_delete(self.binIds, deadRowIndices, axis=0)

#------------------------------------------------------------------------------
# GET / SET

    def getNumStoits(self):
        """return the value of numStoits in the metadata tables"""
        return self.dataManager.getNumStoits(self.dbFileName)

    def getMerColNames(self):
        """return the value of merColNames in the metadata tables"""
        return self.dataManager.getMerColNames(self.dbFileName)

    def getMerSize(self):
        """return the value of merSize in the metadata tables"""
        return self.dataManager.getMerSize(self.dbFileName)

    def getNumMers(self):
        """return the value of numMers in the metadata tables"""
        return self.dataManager.getNumMers(self.dbFileName)

### USE the member vars instead!
#    def getNumCons(self):
#        """return the value of numCons in the metadata tables"""
#        return self.dataManager.getNumCons(self.dbFileName)

    def getNumBins(self):
        """return the value of numBins in the metadata tables"""
        return self.dataManager.getNumBins(self.dbFileName)

    def setNumBins(self, numBins):
        """set the number of bins"""
        self.dataManager.setNumBins(self.dbFileName, numBins)

    def getStoitColNames(self):
        """return the value of stoitColNames in the metadata tables"""
        return np_array(self.dataManager.getStoitColNames(self.dbFileName).split(","))

    def isClustered(self):
        """Has the data been clustered already"""
        return self.dataManager.isClustered(self.dbFileName)

    def setClustered(self):
        """Save that the db has been clustered"""
        self.dataManager.setClustered(self.dbFileName, True)

    def isComplete(self):
        """Has the data been *completely* clustered already"""
        return self.dataManager.isComplete(self.dbFileName)

    def setComplete(self):
        """Save that the db has been completely clustered"""
        self.dataManager.setComplete(self.dbFileName, True)

    def getBinStats(self):
        """Go through all the "bins" array and make a list of unique bin ids vs number of contigs"""
        return self.dataManager.getBinStats(self.dbFileName)

    def setBinStats(self, binStats):
        """Store the valid bin Ids and number of members

        binStats is a list of tuples which looks like:
        [ (bid, numMembers) ]
        Note that this call effectively nukes the existing table
        """
        self.dataManager.setBinStats(self.dbFileName, binStats)
        self.setNumBins(len(binStats))

    def setBinAssignments(self, assignments, nuke=False):
        """Save our bins into the DB"""
        self.dataManager.setBinAssignments(self.dbFileName,
                                           assignments,
                                           nuke=nuke)

    def loadLinks(self):
        """Extra wrapper 'cause I am dumb"""
        self.links = self.getLinks()

    def getLinks(self):
        """Get contig links"""
        # first we get the absolute links
        absolute_links = self.dataManager.restoreLinks(self.dbFileName, self.indices)
        # now convert this into plain old row_indices
        reverse_index_lookup = {}
        for i in range(len(self.indices)):
            reverse_index_lookup[self.indices[i]] = i

        # now convert the absolute links to local ones
        relative_links = {}
        for cid in self.indices:
            local_cid = reverse_index_lookup[cid]
            relative_links[local_cid] = []
            try:
                for link in absolute_links[cid]:
                    relative_links[local_cid].append([reverse_index_lookup[link[0]], link[1], link[2], link[3]])
            except KeyError: # not everyone is linked
                pass

        return relative_links

#------------------------------------------------------------------------------
# DATA TRANSFORMATIONS

    def getAverageCoverage(self, rowIndex):
        """Return the average coverage for this contig across all stoits"""
        return sum(self.transformedCP[rowIndex])/self.numStoits

    def shuffleBAMs(self):
        """Make the data transformation deterministic by reordering the bams"""
        # first we should make a subset of the total data
        # we'd like to take it down to about 1500 or so RI's
        # but we'd like to do this in a repeatable way
        ideal_contig_num = 1500
        sub_cons = range(len(self.indices))
        while len(sub_cons) > ideal_contig_num:
            # select every second contig when sorted by norm cov
            cov_sorted = np_argsort(self.normCoverages[sub_cons])
            sub_cons = np_array([sub_cons[cov_sorted[i*2]] for i in range(int(len(sub_cons)/2))])

            if len(sub_cons) > ideal_contig_num:
                # select every second contig when sorted by mer PC1
                mer_sorted = np_argsort(self.kmerPCs[sub_cons])
                sub_cons = np_array([sub_cons[mer_sorted[i*2]] for i in range(int(len(sub_cons)/2))])

        # now that we have a subset, calculate the distance between each of the untransformed vectors
        num_sc = len(sub_cons)
        # log shift the coverages towards the origin
        sub_covs = np_transpose([self.covProfiles[i]*(np_log10(self.normCoverages[i])/self.normCoverages[i]) for i in sub_cons])
        sq_dists = cdist(sub_covs,sub_covs,'cityblock')
        dists = squareform(sq_dists)

        # initialise a list of left, right neighbours
        lr_dict = {}
        for i in range(self.numStoits):
            lr_dict[i] = []

        too_big = 10000
        while True:
            closest = np_argmin(dists)
            if dists[closest] == too_big:
                break
            (i,j) = self.small2indices(closest, self.numStoits-1)
            lr_dict[j].append(i)
            lr_dict[i].append(j)

            # mark these guys as neighbours
            if len(lr_dict[i]) == 2:
                # no more than 2 neighbours
                sq_dists[i,:] = too_big
                sq_dists[:,i] = too_big
                sq_dists[i,i] = 0.0
            if len(lr_dict[j]) == 2:
                # no more than 2 neighbours
                sq_dists[j,:] = too_big
                sq_dists[:,j] = too_big
                sq_dists[j,j] = 0.0

            # fix the dist matrix
            sq_dists[j,i] = too_big
            sq_dists[i,j] = too_big
            dists = squareform(sq_dists)

        # now make the ordering
        ordering = [0, lr_dict[0][0]]
        done = 2
        while done < self.numStoits:
            last = ordering[done-1]
            if lr_dict[last][0] == ordering[done-2]:
                ordering.append(lr_dict[last][1])
                last = lr_dict[last][1]
            else:
                ordering.append(lr_dict[last][0])
                last = lr_dict[last][0]
            done+=1

        # reshuffle the contig order!
        # yay for bubble sort!
        ordering = np_arange(self.numStoits)
        working = np_arange(self.numStoits)
        for i in range(1, self.numStoits):
            # where is this guy in the list
            loc = list(working).index(ordering[i])
            if loc != i:
                # swap the columns
                self.covProfiles[:,[i,loc]] = self.covProfiles[:,[loc,i]]
                self.stoitColNames[[i,loc]] = self.stoitColNames[[loc,i]]
                working[[i,loc]] = working[[loc,i]]

    def small2indices(self, index, side):
        """Return the indices of the comparative items
        when given an index into a condensed distance matrix
        """
        step = 0
        while index >= (side-step):
            index = index - side + step
            step += 1
        return (step, step + index + 1)

    def transformCP(self, timer, silent=False, nolog=False, min=None, max=None):
        """Do the main transformation on the coverage profile data"""
        shrinkFn = np_log10
        if(nolog):
            shrinkFn = lambda x:x

        self.transformedCP = np_zeros((self.numContigs,3))
        self.corners = np_zeros((self.numStoits,3))

        if(not silent):
            print "    Reticulating splines"
            if self.squish:
                print "    Dimensionality reduction with extra squish"
            else:
                print "    Dimensionality reduction"

        unit_vectors = [(np_cos(i*2*np_pi/self.numStoits),np_sin(i*2*np_pi/self.numStoits)) for i in range(self.numStoits)]

        # make sure the bams are ordered consistently
        if self.numStoits > 3:
            self.shuffleBAMs()

        for i in range(len(self.indices)):
            shifted_vector = np_array([0.0,0.0])
            try:
                flat_vector = (self.covProfiles[i] / sum(self.covProfiles[i]))
            except FloatingPointError:
                flat_vector = self.covProfiles[i]

            for j in range(self.numStoits):
                shifted_vector[0] += unit_vectors[j][0] * flat_vector[j]
                shifted_vector[1] += unit_vectors[j][1] * flat_vector[j]

            # log scale it towards the centre
            scaling_vector = shifted_vector * self.scaleFactor
            sv_size = np_norm(scaling_vector)
            if sv_size > 1:
                shifted_vector /= shrinkFn(sv_size)

            self.transformedCP[i,0] = shifted_vector[0]
            self.transformedCP[i,1] = shifted_vector[1]
            # should always work cause we nuked
            # all 0 coverage vecs in parse
            self.transformedCP[i,2] = shrinkFn(self.normCoverages[i])

        # finally scale the matrix to make it equal in all dimensions
        if(min is None):
            min = np_amin(self.transformedCP, axis=0)
            self.transformedCP -= min
            max = np_amax(self.transformedCP, axis=0)
            max = max / (self.scaleFactor-1)
            self.transformedCP /= max
        else:
            self.transformedCP -= min
            self.transformedCP /= max

        # get the corner points
        XYcorners = np_reshape([i for i in np_array(unit_vectors)],
                               (self.numStoits, 2))

        for i in range(self.numStoits):
            self.corners[i,0] = XYcorners[i,0]
            self.corners[i,1] = XYcorners[i,1]

        # shift the corners to match the space
        self.corners -= min
        self.corners /= max

        # scale the corners to fit the plot
        cmin = np_amin(self.corners, axis=0)
        self.corners -= cmin
        cmax = np_amax(self.corners, axis=0)
        cmax = cmax / (self.scaleFactor-1)
        self.corners[:,0] /= cmax[0]
        self.corners[:,1] /= cmax[1]
        for i in range(self.numStoits):
            self.corners[i,2] = self.scaleFactor + 100


        if self.squish:
            # find the centre of the plot
            centre_stick = np_mean(self.corners, axis=0)
            centre_stick[2] = 0.
            self.transformedCP -= centre_stick
            # squish up
            for i in range(len(self.transformedCP)):
                shift = (self.transformedCP[i][2] / self.scaleFactor)
                mult = np_array([shift, shift, 1.])
                self.transformedCP[i] *= mult
            self.transformedCP += centre_stick

        return(min,max)

#------------------------------------------------------------------------------
# IO and IMAGE RENDERING

    def plotStoitNames(self, ax):
        """Plot stoit names on an existing axes"""
        outer_index = 0
        for corner in self.corners:
            ax.text(corner[0],
                    corner[1],
                    corner[2],
                    self.stoitColNames[outer_index],
                    color='#000000'
                    )
            outer_index += 1

    def plotUnbinned(self, timer, coreCut, transform=True):
        """Plot all contigs over a certain length which are unbinned"""
        self.loadData(timer, condition="((length >= "+str(coreCut)+") & (bid == 0))")

        if transform:
            self.transformCP(timer)
        else:
            if self.numStoits == 3:
                self.transformedCP = self.covProfiles
            else:
                print "Number of stoits != 3. You need to transform"
                self.transformCP(timer)

        fig = plt.figure()
        ax1 = fig.add_subplot(111, projection='3d')
        ax1.scatter(self.transformedCP[:,0], self.transformedCP[:,1], self.transformedCP[:,2], edgecolors=self.contigColors, c=self.contigColors, marker='.')
        self.plotStoitNames(ax1)

        try:
            plt.show()
            plt.close(fig)
        except:
            print "Error showing image", exc_info()[0]
            raise
        del fig

    def plotAll(self, timer, coreCut, transform=True):
        """Plot all contigs over a certain length which are unbinned"""
        self.loadData(timer, condition="((length >= "+str(coreCut)+"))")
        if transform:
            self.transformCP(timer)
        else:
            if self.numStoits == 3:
                self.transformedCP = self.covProfiles
            else:
                print "Number of stoits != 3. You need to transform"
                self.transformCP(timer)

        fig = plt.figure()
        ax1 = fig.add_subplot(111, projection='3d')
        ax1.scatter(self.transformedCP[:,0], self.transformedCP[:,1], self.transformedCP[:,2], edgecolors=self.contigColors, c=self.contigColors, marker='.')
        self.plotStoitNames(ax1)

        try:
            plt.show()
            plt.close(fig)
        except:
            print "Error showing image", exc_info()[0]
            raise
        del fig


    def plotTransViews(self, tag="fordens"):
        """Plot top, side and front views of the transformed data"""
        self.renderTransData(tag+"_top.png",azim = 0, elev = 90)
        self.renderTransData(tag+"_front.png",azim = 0, elev = 0)
        self.renderTransData(tag+"_side.png",azim = 90, elev = 0)

    def renderTransCPData(self,
                          fileName="",
                          show=True,
                          elev=45,
                          azim=45,
                          all=False,
                          showAxis=False,
                          primaryWidth=12,
                          primarySpace=3,
                          dpi=300,
                          format='png',
                          fig=None,
                          highlight=None,
                          restrictedBids=[],
                          alpha=1):
        """Plot transformed data in 3D"""
        del_fig = False
        if(fig is None):
            fig = plt.figure()
            del_fig = True
        else:
            plt.clf()
        if(all):
            myAXINFO = {
                'x': {'i': 0, 'tickdir': 1, 'juggled': (1, 0, 2),
                'color': (0, 0, 0, 0, 0)},
                'y': {'i': 1, 'tickdir': 0, 'juggled': (0, 1, 2),
                'color': (0, 0, 0, 0, 0)},
                'z': {'i': 2, 'tickdir': 0, 'juggled': (0, 2, 1),
                'color': (0, 0, 0, 0, 0)},
            }

            ax = fig.add_subplot(131, projection='3d')
            ax.scatter(self.transformedCP[:,0], self.transformedCP[:,1], self.transformedCP[:,2], edgecolors=self.contigColors, c=self.contigColors, marker='.')
            ax.azim = 0
            ax.elev = 0
            ax.set_xlim3d(0,self.scaleFactor)
            ax.set_ylim3d(0,self.scaleFactor)
            ax.set_zlim3d(0,self.scaleFactor)
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            for axis in ax.w_xaxis, ax.w_yaxis, ax.w_zaxis:
                for elt in axis.get_ticklines() + axis.get_ticklabels():
                    elt.set_visible(False)
            ax.w_xaxis._AXINFO = myAXINFO
            ax.w_yaxis._AXINFO = myAXINFO
            ax.w_zaxis._AXINFO = myAXINFO

            ax = fig.add_subplot(132, projection='3d')
            ax.scatter(self.transformedCP[:,0], self.transformedCP[:,1], self.transformedCP[:,2], edgecolors=self.contigColors, c=self.contigColors, marker='.')
            ax.azim = 90
            ax.elev = 0
            ax.set_xlim3d(0,self.scaleFactor)
            ax.set_ylim3d(0,self.scaleFactor)
            ax.set_zlim3d(0,self.scaleFactor)
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            for axis in ax.w_xaxis, ax.w_yaxis, ax.w_zaxis:
                for elt in axis.get_ticklines() + axis.get_ticklabels():
                    elt.set_visible(False)
            ax.w_xaxis._AXINFO = myAXINFO
            ax.w_yaxis._AXINFO = myAXINFO
            ax.w_zaxis._AXINFO = myAXINFO

            ax = fig.add_subplot(133, projection='3d')
            ax.scatter(self.transformedCP[:,0], self.transformedCP[:,1], self.transformedCP[:,2], edgecolors=self.contigColors, c=self.contigColors, marker='.')
            ax.azim = 0
            ax.elev = 90
            ax.set_xlim3d(0,self.scaleFactor)
            ax.set_ylim3d(0,self.scaleFactor)
            ax.set_zlim3d(0,self.scaleFactor)
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            for axis in ax.w_xaxis, ax.w_yaxis, ax.w_zaxis:
                for elt in axis.get_ticklines() + axis.get_ticklabels():
                    elt.set_visible(False)
            ax.w_xaxis._AXINFO = myAXINFO
            ax.w_yaxis._AXINFO = myAXINFO
            ax.w_zaxis._AXINFO = myAXINFO
        else:
            ax = fig.add_subplot(111, projection='3d')
            if len(restrictedBids) == 0:
                if highlight is None:
                    ax.scatter(self.transformedCP[:,0],
                               self.transformedCP[:,1],
                               self.transformedCP[:,2],
                               edgecolors='none',
                               c=self.contigColors,
                               s=2,
                               marker='.')
                else:
                    #draw the opague guys first
                    ax.scatter(self.transformedCP[:,0],
                               self.transformedCP[:,1],
                               self.transformedCP[:,2],
                               edgecolors='none',
                               c=self.contigColors,
                               s=2,
                               marker='.',
                               alpha=alpha)

                    # now replot the highlighted guys
                    disp_vals = np_array([])
                    disp_cols = np_array([])
                    num_points = 0
                    for bin in highlight:
                        for row_index in bin.rowIndices:
                            num_points += 1
                            disp_vals = np_append(disp_vals, self.transformedCP[row_index])
                            disp_cols = np_append(disp_cols, self.contigColors[row_index])

                    # reshape
                    disp_vals = np_reshape(disp_vals, (num_points, 3))
                    disp_cols = np_reshape(disp_cols, (num_points, 3))
                    ax.scatter(disp_vals[:,0],
                               disp_vals[:,1],
                               disp_vals[:,2],
                               edgecolors='none',
                               c=disp_cols,
                               s=2,
                               marker='.')
            else:
                r_trans = np_array([])
                r_cols=np_array([])
                num_added = 0
                for i in range(len(self.indices)):
                    if self.binIds[i] not in restrictedBids:
                        r_trans = np_append(r_trans, self.transformedCP[i])
                        r_cols = np_append(r_cols, self.contigColors[i])
                        num_added += 1
                r_trans = np_reshape(r_trans, (num_added,3))
                r_cols = np_reshape(r_cols, (num_added,3))
                ax.scatter(r_trans[:,0], r_trans[:,1], r_trans[:,2], edgecolors='none', c=r_cols, s=2, marker='.')
            ax.azim = azim
            ax.elev = elev
            ax.set_xlim3d(0,self.scaleFactor)
            ax.set_ylim3d(0,self.scaleFactor)
            ax.set_zlim3d(0,self.scaleFactor)
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_zticklabels([])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            if(not showAxis):
                ax.set_axis_off()

        if(fileName != ""):
            try:
                if(all):
                    fig.set_size_inches(3*primaryWidth+2*primarySpace,primaryWidth)
                else:
                    fig.set_size_inches(primaryWidth,primaryWidth)
                plt.savefig(fileName,dpi=dpi,format=format)
            except:
                print "Error saving image",fileName, exc_info()[0]
                raise
        elif(show):
            try:
                plt.show()
            except:
                print "Error showing image", exc_info()[0]
                raise
        if del_fig:
            plt.close(fig)
            del fig

###############################################################################
###############################################################################
###############################################################################
###############################################################################
