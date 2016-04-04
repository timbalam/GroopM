###############################################################################
#                                                                             #
#    This library is free software; you can redistribute it and/or            #
#    modify it under the terms of the GNU Lesser General Public               #
#    License as published by the Free Software Foundation; either             #
#    version 3.0 of the License, or (at your option) any later version.       #
#                                                                             #
#    This library is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU        #
#    Lesser General Public License for more details.                          #
#                                                                             #
#    You should have received a copy of the GNU Lesser General Public         #
#    License along with this library.                                         #
#                                                                             #
###############################################################################

__author__ = "Tim Lamberton"
__copyright__ = "Copyright 2015"
__credits__ = ["Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "tim.lamberton@gmail.com"

###############################################################################

from nose.tools import assert_true
import numpy as np
import numpy.random as np_random

# local imports
from tools import assert_equal_arrays, assert_isomorphic
from groopm.hierarchy import (height,
                              maxcoeffs,
                              filter_descendents,
                              ancestors,
                              greedy_clique_by_elimination,
                              connectivity_coeffs,
                              nondescendents_of_maxcoeff,
                              cluster_remove)

###############################################################################
###############################################################################
###############################################################################
###############################################################################

def test_height():
    """Z describes tree:
        0-------+
        2---+   |-6
        1   |-5-+
        |-4-+
        3
    """
    Z = np.array([[1., 3., 1., 2.],
                  [2., 4., 1., 3.],
                  [0., 5., 2., 4.]])
                  
    assert_equal_arrays(height(Z),
                        [2, 2, 2, 1, 0, 1],
                        "`height` returns condensed matrix of lowest common ancestor indices")
                        
def test_maxcoeffs():
    """Z describes tree:
        0-------+
        2---+   |-6
        1   |-5-+
        |-4-+
        3
    """
    Z = np.array([[1., 3., 1., 2.],
                  [2., 4., 1., 3.],
                  [0., 5., 2., 4.]])
                  
    """Assign coefficients:
        1-------+
        0---+   |-0
        0   |-0-+
        |-0-+
        0    
    """
    assert_equal_arrays(maxcoeffs(Z, [1, 0, 0, 0, 0, 0, 0]),
                        [1, 0, 0, 0, 0, 0, 1],
                        "`maxcoeffs` returns max coefficient of descendents in the case of a single "
                        "non-zero coeff")
                                
    """Assign coefficients:
        0-------+
        1---+   |-0
        1   |-2-+
        |-0-+
        0    
    """
    assert_equal_arrays(maxcoeffs(Z, [0, 1, 1, 0, 0, 2, 0]),
                        [0, 1, 1, 0, 1, 2, 2],
                        "`maxcoeffs` returns max coefficients in case of a non-zero leaf and larger "
                        "valued internal coeff")
                                              
    """Assign coefficients:
        0-------+
        0---+   |-0
        0   |-1-+
        |-2-+
        0    
    """
    assert_equal_arrays(maxcoeffs(Z, [0, 0, 0, 0, 2, 1, 0]),
                        [0, 0, 0, 0, 2, 2, 2],
                        "`maxcoeffs` returns max coefficients when a higher leaf is lower valued")
                        
    
def test_filter_descendents():
    """Z describes tree:
        0
        |---7---+
        1       |
                |
        2---+   |-8
            |   |
        3   |-6-+
        |-5-+
        4
    """
    Z = np.array([[3., 4., 1., 2.],
                  [2., 5., 1., 3.],
                  [0., 1., 3., 2.],
                  [6., 7., 4., 5.]])
                  
    assert_equal_arrays(filter_descendents(Z, [5, 6, 7]),
                        [6, 7],
                        "`filter_descendents` removes nodes that are descendents")
    
    
def test_ancestors():
    """Z describes tree
        0
        |---7---+
        1       |
                |
        2---+   |-8
            |   |
        3   |-6-+
        |-5-+
        4
    """
    Z = np.array([[3., 4., 1., 2.],
                  [2., 5., 1., 3.],
                  [0., 1., 3., 2.],
                  [6., 7., 4., 5.]])
                  
    assert_equal_arrays(ancestors(Z, range(5)),
                        [5, 6, 7, 8],
                        "`ancestors` returns ancestors of all leaf clusters")
    
    assert_equal_arrays(ancestors(Z, [1]),
                        [7, 8],
                        "`ancestors` returns ancestors of a single leaf cluster")
    
    assert_equal_arrays(ancestors(Z, [5, 6, 8]),
                        [6, 8],
                        "`ancestors` returns union of ancestors for a path of nodes")
                        
    assert_equal_arrays(ancestors(Z, [5, 6, 8], inclusive=True),
                        [5, 6, 8],
                        "`ancestors` returns union of path nodes including nodes"
                        " themselves when `inclusive` flag is set")
                        
                        
def test_greedy_clique_by_elimination():
    C = np.array([[True , True , False],
                  [True , True , False],
                  [False, False, True ]]) # 0, 1 in clique
    node_perm = np_random.permutation(3)
    C_perm = C[np.ix_(node_perm, node_perm)]
    indices_perm = np.empty(3, dtype=int)
    indices_perm[node_perm] = np.arange(3)
    
    assert_equal_arrays(greedy_clique_by_elimination(C_perm),
                        np.sort(indices_perm[:2]),
                        "`greedy_clique_by_elimination` returns indices of clique")
    
    # two cliques with n-1 connecting edges
    C = np.array([[True , True , True , False, True , True ],
                  [True , True , True , True , False, True ],
                  [True , True , True , True , True , False],
                  [False, True , True , True , True , True ],
                  [True , False, True , True , True , True ],
                  [True , True , False, True , True , True ]]) # 0, 1, 2 and 3, 4, 5 cliques
    node_perm = np_random.permutation(6)
    C_perm = C[np.ix_(node_perm, node_perm)]
    indices_perm = np.empty(6, dtype=int)
    indices_perm[node_perm] = np.arange(6)
    
    assert_true(len(greedy_clique_by_elimination(C_perm)) == 3,
                "`greedy_clique_by_elimination` computes correct clique size for two highly connected equal sized cliques")
                
    # two cliques with universally connected link node
    C = np.array([[True , True , True , True , False, False],
                  [True , True , True , True , False, False],
                  [True , True , True , True , False, False],
                  [True , True , True , True , True , True ],
                  [False, False, False, True , True , True ],
                  [False, False, False, True , True , True ]]) #0, 1, 2, 3 and 3, 4, 5 cliques
    node_perm = np_random.permutation(6)
    C_perm = C[np.ix_(node_perm, node_perm)]
    indices_perm = np.empty(6, dtype=int)
    indices_perm[node_perm] = np.arange(6)
    
    assert_equal_arrays(greedy_clique_by_elimination(C_perm),
                        np.sort(indices_perm[:4]),
                        "`greedy_clique_by_elimination` computes the larger of two overlapping cliques")

                        
def test_connectivity_coeffs():
    """A describes tree:
        0---+
        1   |-4
        |-3-+
        2
    """
    A = np.array([[0, 4, 4],
                  [4, 1, 3],
                  [4, 3, 2]])
    C = np.array([[True , False, False],
                  [False, True , True ],
                  [False, True , True ]]) # 0 and 1, 2 cliques
                  
    (coeffs, nodes) = connectivity_coeffs(A, C)
    assert_equal_arrays(nodes,
                        [0, 1, 2, 3, 4],
                        "`conectivity coeffs` computes coefficients for all ancestor nodes")
    assert_equal_arrays(coeffs,
                        [1, 1, 1, 2, 1],
                        "`connectivity coeffs` computes correct coefficients")
                        
                        
def test_nondescendents_of_maxcoeff():
    """Z describes tree:
        0-------+
        2---+   |-6
        1   |-5-+
        |-4-+
        3
    """
    Z = np.array([[1., 3., 1., 2.],
                  [2., 4., 1., 3.],
                  [0., 5., 2., 4.]])
                  
    """Assign coefficients:
        1-------+
        0---+   |-0
        0   |-0-+
        |-0-+
        0    
    """
    print nondescendents_of_maxcoeff(Z, [1, 0, 0, 0, 0, 0, 0])
    assert_equal_arrays(nondescendents_of_maxcoeff(Z, [1, 0, 0, 0, 0, 0, 0]),
                        [6],
                        "`nondescendents_of_maxcoeffs` returns ancestors of a single "
                        "non-zero coeff")
                                
    """Assign coefficients:
        0-------+
        1---+   |-0
        1   |-2-+
        |-0-+
        0    
    """
    assert_equal_arrays(nondescendents_of_maxcoeff(Z, [0, 1, 1, 0, 0, 2, 0]),
                        [6],
                        "`nondescendents_of_maxcoeffs` returns ancestors of larger "
                        "valued internal coeff")
                                              
    """Assign coefficients:
        0-------+
        0---+   |-0
        0   |-1-+
        |-2-+
        0    
    """
    assert_equal_arrays(nondescendents_of_maxcoeff(Z, [0, 0, 0, 0, 2, 1, 0]),
                        [5, 6],
                        "`nondescendents_of_maxcoeffs` returns ancestors of larger "
                        "valued internal coeff when a higher leaf is lower valued")
                        

def test_cluster_remove():
    """Z describes tree:
        0-------+
        2---+   |-6
        1   |-5-+
        |-4-+
        3
    """
    Z = np.array([[1., 3., 1., 2.],
                  [2., 4., 1., 3.],
                  [0., 5., 2., 4.]])
                                     
    assert_isomorphic(cluster_remove(Z, [5, 6]),
                      [0, 1, 2, 1],
                      "`cluster_remove` computes flat cluster indices after removing "
                      "internal indices")
                
    assert_isomorphic(cluster_remove(Z, [0, 6]),
                      [0, 1, 1, 1],
                      "`cluster_remove` computes flat cluster indices after removing "
                     "a leaf and internal indices")
                        
###############################################################################
###############################################################################
###############################################################################
###############################################################################
