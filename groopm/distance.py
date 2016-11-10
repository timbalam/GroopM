#!/usr/bin/env python
###############################################################################
#                                                                             #
#    distance.py                                                              #
#                                                                             #
#    Working with distance metrics for features                               #
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
import scipy.spatial.distance as sp_distance
import scipy.stats as sp_stats

# local imports

np.seterr(all='raise')

###############################################################################
###############################################################################
###############################################################################
###############################################################################

def mediod(Y):
    """Get member index that minimises the sum distance to other members

    Parameters
    ----------
    Y : ndarray
        Condensed distance matrix containing distances for pairs of
        observations. See scipy's `squareform` function for details.
        
    Returns
    -------
    index : int
        Mediod observation index.
    """
    # for each member, sum of distances to other members
    index = sp_distance.squareform(Y).sum(axis=1).argmin()

    return index
    
    
def argrank(array, weight_fun=None, axis=0):
    """Return the positions of elements of a when sorted along the specified axis"""
    if axis is None:
        return _fractional_rank(array, weight_fun=weight_fun)
    return np.apply_along_axis(_fractional_rank, axis, array, weight_fun=weight_fun)
    
    
def iargrank(out, weight_fun=None):
    """Replace elements with the fractional positions when sorted"""
    _ifractional_rank(out, weight_fun=weight_fun)

    
def core_distance(Y, weight_fun=None, minWt=None, minPts=None):
    """Compute core distance for data points, defined as the distance to the furtherest
    neighbour where the cumulative weight of closer points is less than minWt.

    Parameters
    ----------
    Y : ndarray
        Condensed distance matrix containing distances for pairs of
        observations. See scipy's `squareform` function for details.
    weight_fun : ndarray
        Function to calculate pairwise weights for condensed distances.
    minWt : ndarray
        Total cumulative neighbour weight used to compute density distance for individual points.
    minPts : int
        Number of neighbours used to compute density distance.
        
    Returns
    -------
    core_distance : ndarray
        Core distances for data points.
    """
    (Y, _) = validate_y(Y, name="Y")
    n = sp_distance.num_obs_y(Y)
    #dm_ = sp_distance.squareform(Y)
    core_dist = np.empty(n, dtype=Y.dtype)
    m = np.empty(n, dtype=Y.dtype) # store row distances
    minPts = n-1 if minPts is None else minPts
    if weight_fun is None or minWt is None:
        #dm_.sort(axis=1)
        #x_ = dm_[:, np.minimum(n-1, minPts)]
        for (i, mp) in np.broadcast(np.arange(n), minPts):
            others = np.flatnonzero(np.arange(n)!=i)
            m[others] = Y[condensed_index(n, i, others)]
            m[i] = 0
            m.sort()
            #assert np.all(dm_[i] == m)
            core_dist[i] = m[np.minimum(n-1, mp)]
            #assert x_[i] == core_dist[i]
    else:
        #wm_ = sp_distance.squareform(weights)
        w = np.empty(n, dtype=np.double) # store row weights
        for (i, mp, mw) in np.broadcast(np.arange(n), minPts, minWt):
            others = np.flatnonzero(np.arange(n)!=i)
            m[others] = Y[condensed_index(n, i, others)]
            m[i] = 0
            #assert np.all(m==dm_[i])
            w[others] = weight_fun(i, others)
            w[i] = 0
            #assert np.all(w==wm_[i])
            sorting_indices = m.argsort()
            minPts = np.minimum(int(np.sum(w[sorting_indices].cumsum() < mw)), mp)
            core_dist[i] = m[sorting_indices[np.minimum(n-1, minPts)]]
            #minPts_ = int(np.sum(wm_[i, sorting_indices].cumsum() < minWt[i]))
            #m_ = m[sorting_indices]
            #assert core_dist[i] == np.minimum(m_[np.minimum(n-1, mp)], m_[np.minimum(n-1, minPts_)])
    return core_dist

    
def reachability_order(Y, core_dist=None):
    """Traverse collection of nodes by choosing the closest unvisited node to
    a visited node at each step to produce a reachability plot.
    
    Parameters
    ----------
    Y : ndarray
        Condensed distance matrix
    core_dist : ndarray
        Core distances for original observations of Y.
        
    Returns
    -------
    o : ndarray
        1-D array of indices of original observations in traversal order.
    d : ndarray
        1-D array. `d[i]` is the `i`th traversal distance.
    """
    Y = np.asanyarray(Y)
    n = sp_distance.num_obs_y(Y)
    if core_dist is not None:
        core_dist = np.asarray(core_dist)
        if core_dist.shape != (n,):
            raise ValueError("core_dist is not a 1-D array with compatible size to Y.")
    #dm_ = sp_distance.squareform(Y)
    #dm_ = np.maximum(dm_, core_dist[:, None]) if core_dist is not None else dm_
    o = np.empty(n, dtype=np.intp)
    to_visit = np.ones(n, dtype=bool)
    closest = 0
    o[0] = 0
    to_visit[0] = False
    d = np.empty(n, dtype=Y.dtype)
    d[0] = 0
    d[1:] = Y[condensed_index(n, 0, np.arange(1, n))]
    if core_dist is not None:
        d = np.maximum(d, core_dist[0])
    #assert np.all(d== dm_[0])
    for i in range(1, n):
        closest = np.flatnonzero(to_visit)[d[to_visit].argmin()]
        o[i] = closest
        to_visit[closest] = False
        m = Y[condensed_index(n, closest, np.flatnonzero(to_visit))]
        if core_dist is not None:
            m = np.maximum(m, core_dist[closest])
        #assert np.all(m==dm_[closest, to_visit])
        d[to_visit] = np.minimum(d[to_visit], m)
    return (o, d[o])
    
    
def _condensed_index(n, i, j):
    """
    Calculate the condensed index of element (i, j) in an n x n condensed
    matrix.
    Based on scipy Cython function:
    https://github.com/scipy/scipy/blob/v0.17.0/scipy/cluster/_hierarchy.pyx
    """
    if i < j:
        return n * i - (i * (i + 1) // 2) + (j - i - 1)
    elif i > j:
        return n * j - (j * (j + 1) // 2) + (i - j - 1)
        
condensed_index_ = np.vectorize(_condensed_index, otypes=[np.intp])


def condensed_index(n, i, j):
    """
    Calculate the condensed index of element (i, j) in an n x n condensed
    matrix.
    Based on scipy Cython function:
    https://github.com/scipy/scipy/blob/v0.17.0/scipy/cluster/_hierarchy.pyx
    """
    return np.where(i < j,
                    n*i - (i * (i + 1) // 2) + (j - i - 1),
                    n*j - (j * (j + 1) // 2) + (i - j - 1)
                   )
    
    
def squareform_coords_(n, k):
    """
    Calculate the coordinates (i, j), i < j of condensed index k in full
    n x n distance matrix.
    """
    k = np.asarray(k)
    n = np.asarray(n)
    i = np.floor((1. / 2) * (2*n - 1 - np.sqrt((2*n - 1)**2 - 8 * k))).astype(int)
    j = np.asarray(i + k - (n * i - (i * (i + 1) // 2) - 1), dtype=int) * 1
    return (i, j)
  
    
def squareform_coords(n, k):
    """
    Calculate the coordinates (i, j), i < j of condensed index k in full
    n x n distance matrix.
    """
    n = np.asarray(n)
    k = np.asarray(k)
    # i = np.floor(0.5*(2*n - 1 - np.sqrt((2*n - 1)**2 - 8*k)))
    i = -8.*k
    i += (2*n - 1)**2
    i **= 0.5
    i *= -1
    i += 2*n - 1
    i *= 0.5
    i = np.floor(i).astype(np.int)
    # j = k + i - (n * i - (i * (i + 1)) // 2 - 1)
    j = i + 1
    j *= i
    j //= 2
    j *= -1
    j += n*i - 1
    j *= -1
    j += i
    j += k
    j = np.asarray(j, dtype=np.int)*1
    return (i, j)
    
def _binom_test(x, n, p):
    return sp_stats.binom.sf(x-1, n, p)
    
binom_test = np.vectorize(_binom_test, otypes=[float])

def _g_test(x, n, p):
    # o = [x, n-x], e = [np, n(1-p)]
    stat = 0.
    if x!=0:
        stat += 2. * x * np.log(x / (n * p))
    if x!=n:
        stat += 2. * (n-x) * np.log((n-x) / n*(1-p))
    return sp_stats.chi2.sf(stat, 1)
    
g_test = np.vectorize(_g_test, otypes=[float])
    
    
def pairs(n):
    return np.triu_indices(n, k=1)
    
    
# helpers
def _fractional_rank(a, weight_fun=None):
    """Return sorted of array indices with tied values averaged"""
    (a, _) = validate_y(a, name="a")
    size = a.size
    sorting_index = a.argsort()
    #a_ = a[sorting_index]
    sa = a[sorting_index]
    del a
    #assert np.all(a_==a)
    #flag_ = np.concatenate(([True], a_[1:] != a_[:-1], [True]))
    flag = np.concatenate((sa[1:] != sa[:-1], [True]))
    if weight_fun is None:
        # counts up to 
        sa = np.flatnonzero(flag).astype(float)+1
        #cw_ = np.flatnonzero(flag_).astype(float)
        #assert np.all(cw_[1:]==a)
    else:
        sa = weight_fun(sorting_index).cumsum().astype(float)
        sa = sa[flag]
        #cw_ = np.concatenate(([0.], weights[sorting_index].cumsum())).astype(float)
        #cw_ = cw_[flag_]
        #assert np.all(cw_[1:]==a)
    sa = np.concatenate((sa[:1] - 1, sa[1:] + sa[:-1] - 1)) * 0.5
    #sr_ = (cw_[1:] + cw_[:-1] - 1) * 0.5
    #assert np.all(sr_==a)
    flag = np.concatenate(([0], np.cumsum(flag[:-1])))
    #iflag_ = np.cumsum(flag_[:-1]) - 1
    #assert np.all(iflag_==flag)
    flag = sa[flag]
    sa = np.empty(size, dtype=np.double)
    sa[sorting_index] = flag
    
    #r_ = np.empty(size, dtype=np.double)
    #r_[sorting_index] = sr_[iflag_]
    #assert np.all(r_==a)
    return sa

def _ifractional_rank(a, weight_fun=None):
    """Array value ranks with tied values averaged"""
    (a, _) = validate_y(a, name="a")
    size = a.size
    out = a
    
    sorting_index = a.argsort() # copy!
    #a_ = a[sorting_index]
    a[:] = a[sorting_index] # sort a
    #assert np.all(a_==a)
    #flag_ = np.concatenate(([True], a_[1:] != a_[:-1], [True]))
    flag = np.concatenate((a[1:] != a[:-1], [True]))
    #flag__ = np.empty(size, dtype=bool)
    #flag__[-1] = True
    #flag__[:-1] = a[1:] != a[:-1]
    #assert np.all(flag__==flag)
    buff = np.getbuffer(a)
    del a # a invalid
    nnz = np.count_nonzero(flag)
    
    if weight_fun is None:
        # counts up to 
        r = np.frombuffer(buff, dtype=np.double, count=nnz) # reserve part of buffer for rest of cumulative sorted weights
        r[:] = np.flatnonzero(flag)+1
        #cw_ = np.flatnonzero(flag_).astype(np.double)
        #assert np.all(cw_[1:]==r)
    else:
        cw = np.frombuffer(buff, dtype=np.double)
        cw[:] = weight_fun(sorting_index)  # write sorted weights into buffer
        cw[:] = cw.cumsum()
        r = np.frombuffer(buff, dtype=np.double, count=nnz)
        r[:] = cw[flag]
        del cw # cw invalid
        #cw_ = np.concatenate(([0.], weights[sorting_index].cumsum())).astype(np.double)
        #cw_ = cw_[flag_]
        #assert np.all(cw_[1:]==r)
    
    # compute average ranks of tied values
    if len(r) > 1:
        r[1:] = r[1:] + r[:-1]
        r[1:] -= 1
        r[1:] *= 0.5
    r[0] = (r[0] - 1) * 0.5
    
    #sr_ = (cw_[1:] + cw_[:-1] - 1) * 0.5
    #assert np.all(sr_==r)
    #iflag = np.empty(size, dtype=np.int)
    #iflag[0] = 0
    iflag = np.cumsum(flag[:-1]) # another copy !
    del flag # mem_opt
    #iflag_ = np.cumsum(flag_[:-1]) - 1
    #assert np.all(iflag_[1:]==iflag)
    top = r[0] # get this value first, as r and out share a buffer, and writing to out will overwrite r 
    out[sorting_index[1:]] = r[iflag]
    out[sorting_index[0]] = top
    
    #out_ = np.empty(size, dtype=np.double)
    #out_[sorting_index] = sr_[iflag_]
    #assert np.all(out_==out)


def validate_y(Y, weights=None, name="Y"):
    Y = np.asanyarray(Y)
    size = Y.size
    if Y.shape != (size,):
        raise ValueError("%s should be a 1-D array." % name)
    
    if weights is not None:
        weights = np.asanyarray(weights)
        if weights.shape != (size,):
            raise ValueError("weights should have the same shape as %s." % name)
    return (Y, weights)  
    
###############################################################################
###############################################################################
###############################################################################
###############################################################################
