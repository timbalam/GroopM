#!/usr/bin/env python
###############################################################################
#                                                                             #
#    plot.py                                                                  #
#                                                                             #
#    Data visualisation                                                       #
#                                                                             #
#    Copyright (C) Michael Imelfort, Tim Lamberton                            #
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

__author__ = "Michael Imelfort, Tim Lamberton"
__copyright__ = "Copyright 2012-2015"
__credits__ = ["Michael Imelfort", "Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "t.lamberton@uq.edu.au"
__status__ = "Development"

###############################################################################
import os
import sys
import colorsys
import operator
import numpy as np
import scipy.spatial.distance as sp_distance
import matplotlib.pyplot as plt
import matplotlib.colors as plt_colors
import matplotlib.cm as plt_cm
from mpl_toolkits.mplot3d import axes3d, Axes3D


# GroopM imports
from utils import makeSurePathExists
from profileManager import ProfileManager
from binManager import BinManager
from mstore import ContigParser
import distance
import hierarchy

np.seterr(all='raise')

###############################################################################
###############################################################################
###############################################################################
###############################################################################
class BinPlotter:
    """Plot and highlight contigs from a bin"""
    def __init__(self, dbFileName, folder=None):
        self._pm = ProfileManager(dbFileName)
        self._outDir = os.getcwd() if folder == "" else folder
        # make the dir if need be
        if self._outDir is not None:
            makeSurePathExists(self._outDir)

    def loadProfile(self, timer):
        return self._pm.loadData(timer, loadBins=True, minLength=0, removeBins=True, bids=[0])

    def plot(self,
             timer,
             bids=None,
             origin="mediod",
             colorMap="HSV",
             prefix="BIN"
            ):
        
        profile = self.loadProfile(timer)

        bm = BinManager(profile)
        if bids is None or len(bids) == 0:
            bids = bm.getBids()
        else:
            bm.checkBids(bids)

        fplot = BinDistancePlotter(profile, colourmap=colorMap)
        print "    %s" % timer.getTimeStamp()
        
        for bid in bids:
            fileName = "" if self._outDir is None else os.path.join(self._outDir, "%s_%d.png" % (prefix, bid))

            fplot.plot(fileName=fileName,
                       origin=origin,
                       bid=bid)
                       
            if fileName=="":
                break
        print "    %s" % timer.getTimeStamp()

        
class ProfilePlotter:
    """Plot and highlight contigs from a bin"""
    def __init__(self, dbFileName, folder=None):
        self._pm = ProfileManager(dbFileName)
        self._outDir = os.getcwd() if folder == "" else folder
        # make the dir if need be
        if self._outDir is not None:
            makeSurePathExists(self._outDir)
            
    def loadProfile(self, timer):
        return self._pm.loadData(timer, loadBins=True, minLength=0, removeBins=True, bids=[0])
        
    def plot(self,
             timer,
             bids=None,
             origin="mediod",
             colorMap="HSV",
             prefix="BIN"
            ):
        
        profile = self.loadProfile(timer)

        fplot = BinDistancePlotter(profile, colourmap=colorMap)
        fplot.setup()
        print "    %s" % timer.getTimeStamp()
        
        fileName = "" if self._outDir is None else os.path.join(self._outDir, "%s_%s.png" % (prefix, "tree"))
        fplot.plot(fileName=fileName)
        print "    %s" % timer.getTimeStamp()

        
# Basic plotting tools
class GenericPlotter:
    def plot(self, fileName=""):
        # plot contigs in coverage space
        fig = plt.figure()

        self.plotOnFig(fig)

        if(fileName != ""):
            try:
                fig.set_size_inches(15,15)
                plt.savefig(fileName,dpi=300)
            except:
                print "Error saving image:", fileName, sys.exc_info()[0]
                raise
        else:
            print "Plotting"
            try:
                plt.show()
            except:
                print "Error showing image", sys.exc_info()[0]
                raise

        plt.close(fig)
        del fig
        
    def plotOnFig(self, fig): pass


class Plotter2D(GenericPlotter):
    def plotOnFig(self, fig):
        ax = fig.add_subplot(111)
        self.plotOnAx(ax)
            
    def plotOnAx(self, ax): pass

    
class Plotter3D(GenericPlotter):
    def plotOnFig(self, fig):
        ax = fig.add_subplot(111, projection='3d')
        self.plotOnAx(ax)
        
    def plotOnAx(self, ax): pass
    
    
# Plot types
class FeatureAxisPlotter:
    def __init__(x, y,
                 colours,
                 sizes,
                 colourmap,
                 edgecolours,
                 z=None,
                 xlabel="", ylabel="", zlabel=""):
        """
        Parameters
        ------
        x: array_like, shape (n,)
        y: array_like, shape (n,)
        colours: color or sequence of color
        sizes: scalar or array_like, shape (n,)
        colourmap: Colormap
        edgecolours: color or sequence of color
        z: array_like, shape (n,), optional
        xlabel: string, optional
        ylabel: string, optional
        zlabel: string, optional
        """
        self.x = x
        self.y = y
        self.z = z
        self.colours = colours
        self.colourmap = colourmap
        self.edgecolours = colours
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel
    
    def __call__(self, ax):
        
        coords = (self.x, self.y)
        try:
            coords += (self.z,)
        except:
            pass
        sc = ax.scatter(*coords,
                        c=self.colours, s=self.sizes,
                        cmap=self.colourmap,
                        vmin=0., vmax=1., marker='.')                        
        sc.set_edgecolors(self.edgecolours)
        sc.set_edgecolors = sc.set_facecolors = lambda *args:None
        
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        if len(coords) == 3:
            ax.set_zlabel(self.zlabel)

            
class FeaturePlotter(Plotter2D): 
    def __init__(self, *args, **kwargs):
        self.plotOnAx = FeatureAxisPlotter(*args, **kwargs)


class SurfacePlotter(Plotter3D):
    def __init__(self, *args, **kwargs):
        self.plotOnAx = FeatureAxisPlotter(*args, **kwargs)
            

class HierarchyAxisPlotter:
    def __init__(self, Z,
                 link_colour_func,
                 leaf_label_func,
                 xlabel="", ylabel=""):
        """
        Fields
        ------
        Z: linkage matrix, shape(n, 4)
        link_colour_func: callable
        leaf_label_func: callable
        xlabel: string
        ylabel: string
        """
        self.Z = Z
        self.link_colour_func = link_colour_func
        self.leaf_label_func = leaf_label_func
        self.xlabel = xlabel
        self.ylabel = ylabel
    
    def __call__(self, ax):
        sp_hierarchy.dendrogram(self.Z, ax=ax, p=1000,
                                truncate_mode='lastp',
                                distance_sort='ascending',
                                color_threshold=0,
                                leaf_label_func=self.label_label_func,
                                link_color_func=self.link_colour_func)
        
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        

# Tree plotters
class HierarchyRemovedPlotter:
    def __init__(self, profile, threshold=1, greedy=False):
        self._profile = profile
        x = sp_distance.pdist(self._profile.covProfiles, metric="euclidean")
        y = sp_distance.pdist(self._profile.kmerSigs, metric="euclidean")
        w = sp_distance.pdist(self._profile.contigLengths[:, None], operator.mul)
        rnorm = np_linalg.norm(distance.argrank((x, y), weights=w, axis=1), axis=0)
        self._Z = sp_hierarchy.average(rnorm)
        ct = ClassificationCoherenceClusterTool(self._profile.markers)
        (self._mcc, self._mnodes) = ct.classification_coherence(Z, threshold)
        
    def plot(self,
             greedy=False,
             fileName=""):
        
        n = self._Z.shape[1]
        cc = np.zeros(2*n - 1, dtype=self._mcc.dtype)
        cc[self._mnodes] = np.where(self._mcc < 0, 0, self._mcc)
        rootinds = hierarchy.maxcoeff_roots(Z, cc)
        rootancestors = ancestors(Z, rootinds)
        
        if greedy:
            rootinds = np.intersect1d(mnodes, rootancestors)
            rootancestors = hierarchy.ancestors(Z, rootinds, inclusive=True)
            
        rootancestors_set = set(rootancestors)
        hplot = HierarchyPlotter(
            self.Z,
            link_colour_func=lambda k: 'k' if k in rootancestors_set else 'r',
            leaf_label_func=lambda k: jj,
            xlabel="cov", ylabel="rnorm"
        )
        hplot.plot(fileName)
        
        
        
        
  
  
# Bin plotters
class BinDistancePlotter:
    def __init__(self, profile, colourmap='HSV'):
        self._profile = profile
        self._colourmap = getColorMap(colourmap)
        x = sp_distance.pdist(self._profile.covProfiles, metric="euclidean")
        y = sp_distance.pdist(self._profile.kmerSigs, metric="euclidean")
        w = sp_distance.pdist(self._profile.contigLengths[:, None], operator.mul)
        scale_factor = 1./w.sum()
        self._x = distance.argrank(x, weights=w)*scale_factor
        self._y = distance.argrank(y, weights=w)*scale_factor
        self._w = w
        self._c = sp_distance.pdist(self._profile.contigGCs[:, None], lambda a, b: (a+b)/2)
        self._h = sp_distance.pdist(self._profile.binIds[:, None], lambda a, b: a!=0 and a==b).astype(bool)
        
    def plot(self,
             bid,
             origin,
             fileName=""):
        
        n = self._profile.numContigs
        bin_indices = BinManager(self._profile).getBinIndices(bid)
        if origin=="mediod":
            bin_squareform_indices = distance.pcoords(bin_indices, n)
            origin = distance.mediod(np.linalg.norm((self._x[bin_squareform_indices], self._y[bin_squareform_indices]), axis=0))
        elif origin=="max_coverage":
            origin = np.argmax(self._profile.normCoverages[bin_indices])
        elif origin=="max_length":
            origin = np.argmax(self._profile.contigLengths[bin_indices])
        else:
            raise ValueError("Invalid `origin` argument parameter value: `%s`" % origin)
        
        indices = distance.ccoords(bin_indices[origin], np.arange(n), n)[0]
        fplot = FeaturePlotter(self._x[indices],
                               self._y[indices],
                               colours=self._c[indices],
                               sizes=20,
                               edgecolours=np.where(self._h[indices], 'r', 'k'),
                               colourmap=self._colourmap,
                               xlabel="cov", ylabel="kmer")
        fplot.plot(fileName)
        

#------------------------------------------------------------------------------
# Helpers
    
def getColorMap(colorMapStr):
    if colorMapStr == 'HSV':
        S = 1.0
        V = 1.0
        return plt_colors.LinearSegmentedColormap.from_list('GC', [colorsys.hsv_to_rgb((1.0 + np.sin(np.pi * (val/1000.0) - np.pi/2))/2., S, V) for val in xrange(0, 1000)], N=1000)
    elif colorMapStr == 'Accent':
        return plt_cm.get_cmap('Accent')
    elif colorMapStr == 'Blues':
        return plt_cm.get_cmap('Blues')
    elif colorMapStr == 'Spectral':
        return plt_cm.get_cmap('spectral')
    elif colorMapStr == 'Grayscale':
        return plt_cm.get_cmap('gist_yarg')
    elif colorMapStr == 'Discrete':
        discrete_map = [(0,0,0)]
        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))

        discrete_map.append((0,0,0))
        discrete_map.append((141/255.0,211/255.0,199/255.0))
        discrete_map.append((255/255.0,255/255.0,179/255.0))
        discrete_map.append((190/255.0,186/255.0,218/255.0))
        discrete_map.append((251/255.0,128/255.0,114/255.0))
        discrete_map.append((128/255.0,177/255.0,211/255.0))
        discrete_map.append((253/255.0,180/255.0,98/255.0))
        discrete_map.append((179/255.0,222/255.0,105/255.0))
        discrete_map.append((252/255.0,205/255.0,229/255.0))
        discrete_map.append((217/255.0,217/255.0,217/255.0))
        discrete_map.append((188/255.0,128/255.0,189/255.0))
        discrete_map.append((204/255.0,235/255.0,197/255.0))
        discrete_map.append((255/255.0,237/255.0,111/255.0))
        discrete_map.append((1,1,1))

        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))
        return plt_colors.LinearSegmentedColormap.from_list('GC_DISCRETE', discrete_map, N=20)

    elif colorMapStr == 'DiscretePaired':
        discrete_map = [(0,0,0)]
        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))

        discrete_map.append((0,0,0))
        discrete_map.append((166/255.0,206/255.0,227/255.0))
        discrete_map.append((31/255.0,120/255.0,180/255.0))
        discrete_map.append((178/255.0,223/255.0,138/255.0))
        discrete_map.append((51/255.0,160/255.0,44/255.0))
        discrete_map.append((251/255.0,154/255.0,153/255.0))
        discrete_map.append((227/255.0,26/255.0,28/255.0))
        discrete_map.append((253/255.0,191/255.0,111/255.0))
        discrete_map.append((255/255.0,127/255.0,0/255.0))
        discrete_map.append((202/255.0,178/255.0,214/255.0))
        discrete_map.append((106/255.0,61/255.0,154/255.0))
        discrete_map.append((255/255.0,255/255.0,179/255.0))
        discrete_map.append((217/255.0,95/255.0,2/255.0))
        discrete_map.append((1,1,1))

        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))
        discrete_map.append((0,0,0))
        return plt_colors.LinearSegmentedColormap.from_list('GC_DISCRETE', discrete_map, N=20)


###############################################################################
###############################################################################
###############################################################################
###############################################################################