#!/usr/bin/env python
###############################################################################
#                                                                             #
#    data3.py                                                                 #
#                                                                             #
#    GroopM - Low level data management and file parsing                      #
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
__copyright__ = "Copyright 2012-2016"
__credits__ = ["Michael Imelfort", "Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "t.lamberton@uq.edu.au"

__current_GMDB_version__ = 6

###############################################################################

import sys
from os.path import splitext as op_splitext, basename as op_basename
from string import maketrans as s_maketrans

import tables
import numpy as np
import numpy.linalg as np_linalg
import tempdir

# GroopM imports
from utils import CSVReader, FastaReader
from map import SingleMMapper, GraftMMapper
from groopmExceptions import BadTaxonomicStringException

# BamM imports
try:
    from bamm.bamParser import BamParser as BMBP
    from bamm.cWrapper import *
    from bamm.bamFile import BM_coverageType as BMCT
except ImportError:
    print """ERROR: There was an error importing BamM. This probably means that
BamM is not installed properly or not in your PYTHONPATH. Installation
instructions for BamM are located at:

    http://ecogenomics.github.io/BamM

If you're sure that BamM is installed (properly) then check your PYTHONPATH. If
you still encounter this error. Please lodge a bug report at:

    http://github.com/ecogenomics/BamM/issues

Exiting...
--------------------------------------------------------------------------------
"""
    sys.exit(-1)

np.seterr(all='raise')

# shut up pytables!
import warnings
warnings.filterwarnings('ignore', category=tables.NaturalNameWarning)

###############################################################################
###############################################################################
###############################################################################
###############################################################################
class DataManager:
    """Top level class for manipulating GroopM data

    Use this class for parsing in raw data into a hdf DB and
    for reading from and updating same DB

    NOTE: All tables are kept in the same order indexed by the contig ID except:
        -mappings and classification tables are indexed by the mapping ID
    """
    
    #Tables managed by this class are listed below:
    #
    #------------------------
    # PROFILES
    #group = '/profile'
    #------------------------
    # **Kmer Signature**
    #table = 'kms'
    kms_desc = lambda self, mers: [(mer, float) for mer in mers]
    #
    # **Kmer Vals**
    #[version < 6] 
    #table = 'kpca'
    #kpca_desc = lambda n: [('pc%d' % i, float) for i in range(n)]
    #
    # **Coverage profile**
    #table = 'coverage'
    coverage_desc = lambda self, cols: [(col, float) for col in cols]
    #
    # **Transformed coverage profile**
    #[version < 6]
    #table = 'transCoverage'
    #transCoverage_desc = [('x', float), ('y', float), ('z', float)]
    #
    # **Coverage profile norms**
    #table = 'normCoverage'
    normCoverage_desc = [('normCov', float)]
    #     
    #------------------------
    # LINKS
    #group = '/links'
    #------------------------
    # ** Links **
    #table = 'links'
    links_desc = [('contig1', int),             # reference to index in meta/contigs
                  ('contig2', int),             # reference to index in meta/contigs
                  ('numReads', int),            # number of reads supporting this link
                  ('linkType', int),            # the type of the link (SS, SE, ES, EE)
                  ('gap', int)                  # the estimated gap between the contigs
                  ]
    #               
    #------------------------
    # MAPPINGS
    #[version >= 6]
    #group = '/mappings'
    #------------------------
    # **Mappings***
    #table = 'mappings'
    mappings_desc = [('marker', int),               # reference to index in meta/markers
                     ('contig', int),               # reference to index in meta/contigs
                     ('taxstring', '|S512')         # original taxstring
                     ]
    #
    # **Mapping classifications***
    #table = 'classification'
    classification_desc = [('domain', int),         # reference to index in meta/taxons
                           ('phylum', int),
                           ('class', int),
                           ('order', int),
                           ('family', int),
                           ('genus', int),
                           ('species', int)
                           ]
    #              
    #------------------------
    # METADATA
    #group = '/meta'
    #------------------------
    # ** Metadata **
    #table = 'meta'
    meta_desc = [('stoitColNames', '|S512'),
                 ('numStoits', int),
                 ('merColNames', '|S4096'),
                 ('merSize', int),
                 ('numMers', int),
                 ('numCons', int),
                 ('numBins', int),
                 ('numMarkers', int),           #[version >= 6]
                 ('clustered', bool),           # set to true after clustering is complete
                 ('complete', bool),            # set to true after clustering finishing is complete
                 ('formatVersion', int)         # groopm file version
                 ]
    #
    # **PC variance**
    #[version < 6]
    #table = 'kpca_variance'
    #kpca_variance = lambda n: [("pc%d_var" % i, float) for i in range(n)]
    #
    # ** Contigs **
    #table = 'contigs'
    contigs_desc = [('cid', '|S512'),
                    ('bid', int),
                    ('length', int),
                    ('gc', float)
                    ]
    #
    # ** Reachability **
    #[version >= 6]
    #table = 'reachability'
    reachability_desc = [('contig', int),       # reference to index in meta/contigs
                         ('distance', float)
                         ]
    #
    # ** Bins **
    #table = 'bins'
    bins_desc = [('bid', int),
                 ('numMembers', int),
                 ('isLikelyChimeric', bool)
                 ]
    #
    # ** Markers **  
    #[version >= 6]
    #table = 'markers'
    markers_desc = [('markerid', '|S512'),
                    ('numMappings', int)
                    ]
    #
    # ** Taxons **
    #[version >= 6]
    #table = 'taxons'
    taxons_desc = [('taxonid', '|S512')
                   ]
    #
    # **Transformed coverage corners**
    #[version < 6]
    #table = 'transCoverageCorners'
    #transCoverageCorners_desc = [('x', float), ('y', float), ('z', float)]
                             

#------------------------------------------------------------------------------
# DB CREATION / INITIALISATION

    def createDB(self, timer, bamFiles, contigsFile, dbFileName, cutoff, kmerSize=4, markerFile=None, 
            workingDirectory=None, graftmPackageList=None, force=False, threads=1):
        """Main wrapper for parsing all input files"""
        
        # make sure we're only overwriting existing DBs with the users consent
        try:
            with open(dbFileName) as f:
                if(not force):
                    user_option = self.promptOnOverwrite(dbFileName)
                    if(user_option != "Y"):
                        print "Operation cancelled"
                        return False
                    else:
                        print "Overwriting database",dbFileName
        except IOError as e:
            print "Creating new database", dbFileName

        # helper instances
        kse = KmerSigEngine(kmerSize)
        cfe = ClassificationEngine()
        conParser = ContigParser()
        bamParser = BamParser()
        mapper = Mapper(working_directory=workingDirectory,
                        graftm_package_list=graftmPackageList,
                        marker_file=markerFile)
        
        # create the db
        try:
            with tables.open_file(dbFileName, mode = "w", title = "GroopM") as h5file:
                # Create groups under "/" (root) for storing profile information and metadata
                profile_group = h5file.create_group("/", "profile", "Assembly profiles")
                meta_group = h5file.create_group("/", "meta", "Associated metadata")
                links_group = h5file.create_group("/", "links", "Paired read link information")
                mappings_group = h5file.create_group("/", "mappings", "Contig mappings")
                
                #------------------------
                # parse contigs
                #
                # Contig IDs in the database are used to link coverage and mapping
                # information from other input files.
                #
                # Before writing to the database we will remove any of them having
                # 0 coverage @ all stoits.
                #------------------------
                import mimetypes
                GM_open = open
                try:
                    # handle gzipped files
                    mime = mimetypes.guess_type(contigsFile)
                    if mime[1] == 'gzip':
                        import gzip
                        GM_open = gzip.open
                except:
                    print "Error when guessing contig file mimetype"
                    raise
                with GM_open(contigsFile, "r") as f:
                    try:
                        (con_names, con_gcs, con_lengths, con_ksigs) = conParser.parse(f, cutoff, kse)
                        num_cons = len(con_names)
                    except:
                        print "Error parsing contigs"
                        raise

                #------------------------
                # parse bam files
                #------------------------
                cid_2_indices = dict(zip(con_names, range(num_cons)))
                (ordered_bamFiles, rowwise_links, cov_profiles) = bamParser.parse(bamFiles,
                                                                                  con_names,
                                                                                  cid_2_indices,
                                                                                  threads)
                tot_cov = [sum(profile) for profile in cov_profiles]
                good_indices = [i for (i, cov) in enumerate(tot_cov) if cov > 0]
                bad_indices = [i for i in range(num_cons) if i not in good_indices]

                if len(bad_indices) > 0:
                    # report the bad contigs to the user
                    # and strip them before writing to the DB
                    print "****************************************************************"
                    print " IMPORTANT! - there are %d contigs with 0 coverage" % len(bad_indices)
                    print " across all stoits. They will be ignored:"
                    print "****************************************************************"
                    for i in xrange(0, min(5, len(bad_indices))):
                        print con_names[bad_indices[i]]
                    if len(bad_indices) > 5:
                      print '(+ %d additional contigs)' % (len(bad_indices)-5)
                    print "****************************************************************"

                    con_names = con_names[good_indices]
                    con_lengths = con_lengths[good_indices]
                    con_gcs = con_gcs[good_indices]
                    cov_profiles = cov_profiles[good_indices]
                    con_ksigs = con_ksigs[good_indices]

                num_cons = len(good_indices)
                cid_2_indices = dict(zip(con_names, range(num_cons)))
                
                #------------------------
                # parse mapping files
                #------------------------
                (contig_indices, marker_indices, marker_names, marker_counts, taxstrings) = mapper.getMappings(contigsFile, cid_2_indices) 
                (tax_table, taxon_names) = cfe.parse(taxstrings)
                num_mappings = len(contig_indices)
                num_markers = len(marker_names)
                
                #------------------------
                # write kmer sigs
                #------------------------
                # store the raw calculated kmer sigs in one table
                kms_data = np.array([tuple(i) for i in con_ksigs], dtype=self.kms_desc(kse.kmerCols))
                h5file.create_table(profile_group,
                                    'kms',
                                    kms_data,
                                    title='Kmer signatures',
                                    expectedrows=num_cons
                                    )

                #------------------------
                # write cov profiles
                #------------------------
                # build a table template based on the number of bamfiles we have
                # _get_bam_descriptor rips off the ".bam" part of bam filenames
                stoitColNames = np.array([_get_bam_descriptor(bf, i+1) for (i, bf) in enumerate(ordered_bamFiles)])
                coverage_data = np.array([tuple(i) for i in cov_profiles], dtype=self.coverage_desc(stoitColNames))
                h5file.create_table(profile_group,
                                    'coverage',
                                    coverage_data,
                                    title="Bam based coverage",
                                    expectedrows=num_cons
                                    )

                # coverage norms
                norm_coverages = np.linalg.norm(cov_profiles, axis=1)
                normCoverages_data = np.array(norm_coverages, dtype=self.normCoverage_desc)
                h5file.create_table(profile_group,
                                    'normCoverage',
                                    normCoverages_data,
                                    title="Normalised coverage",
                                    expectedrows=num_cons
                                    )
                                    
                #------------------------
                # write mappings
                #------------------------
                mappings_data = np.array(zip(marker_indices, contig_indices, taxstrings), dtype=self.mappings_desc)
                h5file.create_table(mappings_group,
                                    "mappings",
                                    mappings_data,
                                    title="Marker mappings",
                                    expectedrows=num_mappings
                                    )
                    
                #------------------------
                # write classifications
                #------------------------
                classification_data = np.array([tuple(i) for i in tax_table], dtype=self.classification_desc)
                h5file.create_table(mappings_group,
                                    "classification",
                                    classification_data,
                                    title="Mapping classifications",
                                    expectedrows=num_mappings
                                    )
                                   
                #------------------------
                # contig links
                #------------------------
                # set table size according to the number of links returned from
                # the previous call
                links_data = np.array(rowwise_links, dtype=self.links_desc)
                h5file.create_table(links_group,
                                    'links',
                                    links_data,
                                    title="Contig Links",
                                    expectedrows=len(rowwise_links)
                                    )

                #------------------------
                # Add a table for the contig metadata
                #------------------------
                contigs_data = np.array(zip(con_names, [0]*num_cons, con_lengths, con_gcs),
                                        dtype=self.contigs_desc)
                h5file.create_table(meta_group,
                                    'contigs',
                                    contigs_data,
                                    title="Contig information",
                                    expectedrows=num_cons
                                    )

                #------------------------
                # Add a table for the bins
                #------------------------
                bins_data = np.array([], dtype=self.bins_desc)
                h5file.create_table(meta_group,
                                    'bins',
                                    bins_data,
                                    title="Bin information",
                                    expectedrows=1
                                    )
                                    
                #------------------------
                # Add a table for reachability info
                #------------------------
                reachability_data = np.array([], dtype=self.reachability_desc)
                h5file.create_table(meta_group,
                                    'reachability',
                                    reachability_data,
                                    title="Reachability information",
                                    expectedrows=1
                                    )
                                    
                #------------------------
                # Add a table for markers
                #------------------------    
                markers_data = np.array(zip(marker_names, marker_counts), dtype=self.markers_desc)
                h5file.create_table(meta_group,
                                    "markers",
                                    markers_data,
                                    title="Marker information",
                                    expectedrows=num_markers
                                    )
                
                #------------------------
                # Add a table for taxons
                #------------------------
                taxons_data = np.array([(i,) for i in taxon_names], dtype=self.taxons_desc)
                h5file.create_table(meta_group,
                                    "taxons",
                                    taxons_data,
                                    title="Taxon information",
                                    expectedrows=len(taxon_names)
                                    ) 
                                    
                #------------------------
                # Add metadata
                #------------------------
                meta_data = np.array([(",".join(stoitColNames),
                                       len(stoitColNames),
                                       ",".join(kse.kmerCols),
                                       kmerSize,
                                       len(kse.kmerCols),
                                       num_cons,
                                       0,
                                       num_markers,
                                       False,
                                       False,
                                       __current_GMDB_version__)],
                                     dtype=self.meta_desc)
                h5file.create_table(meta_group,
                                    'meta',
                                    meta_data,
                                    title="Descriptive data",
                                    expectedrows=1)
                    
                

        except:
            print "Error creating database:", dbFileName, sys.exc_info()[0]
            raise

        print "****************************************************************"
        print "Data loaded successfully!"
        print " -> %d contigs" % num_cons
        print " -> %d BAM files" % len(stoitColNames)
        print " -> %d hits to %d markers" % (num_mappings, num_markers)
        print "Written to: '%s'" % dbFileName
        print "****************************************************************"
        print "    %s" % timer.getTimeStamp()

        # all good!
        return True

    def promptOnOverwrite(self, dbFileName, minimal=False):
        """Check that the user is ok with overwriting the db"""
        input_not_ok = True
        valid_responses = ['Y','N']
        vrs = ",".join([str.lower(str(x)) for x in valid_responses])
        while(input_not_ok):
            if(minimal):
                option = raw_input(" Overwrite? ("+vrs+") : ")
            else:

                option = raw_input(" ****WARNING**** Database: '"+dbFileName+"' exists.\n" \
                                   " If you continue you *WILL* delete any previous analyses!\n" \
                                   " Overwrite? ("+vrs+") : ")
            if(option.upper() in valid_responses):
                print "****************************************************************"
                return option.upper()
            else:
                print "Error, unrecognised choice '"+option.upper()+"'"
                minimal = True

#------------------------------------------------------------------------------
# DB Upgrade
        
    def checkAndUpgradeDB(self, dbFileName, timer, silent=False):
        """Check the DB and upgrade if necessary"""
        # get the DB format version
        this_DB_version = self.getGMDBFormat(dbFileName)
        if __current_GMDB_version__ == this_DB_version:
            if not silent:
                print "    GroopM DB version (%s) up to date" % this_DB_version
            return

        # now, if we get here then we need to do some work
        upgrade_tasks = {}
        upgrade_tasks[(0,1)] = self.upgradeDB_0_to_1
        upgrade_tasks[(1,2)] = self.upgradeDB_1_to_2
        upgrade_tasks[(2,3)] = self.upgradeDB_2_to_3
        upgrade_tasks[(3,4)] = self.upgradeDB_3_to_4
        upgrade_tasks[(4,5)] = self.upgradeDB_4_to_5
        upgrade_tasks[(5,6)] = self.upgradeDB_5_to_6

        # we need to apply upgrades in order!
        # keep applying the upgrades as long as we need to
        try:
            while this_DB_version < __current_GMDB_version__:
                task = (this_DB_version, this_DB_version+1)
                upgrade_tasks[task](dbFileName)
                this_DB_version += 1
        except:
            print "    Error upgrading database to version %d" % (this_DB_version+1)
            raise
            
        if not silent:
            print "    %s" % timer.getTimeStamp()

    def upgradeDB_0_to_1(self, dbFileName):
        """Upgrade a GM db from version 0 to version 1"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 0 to version 1 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the first
        # two kmerSig PCA's in a separate table
        print "    Calculating and storing the kmerSig PCAs"

        # don't compute the PCA of the ksigs just store dummy data
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = _DB1_PCAKsigs(ksigs)
        num_cons = len(pc_ksigs)

        DB1_kpca_desc = [('pc1', float),
                         ('pc2', float)]
        with tables.open_file(dbFileName, mode='a', root_uep="/profile") as h5file:
            h5file.create_table("/",
                                'kpca',
                                np.array(pc_ksigs, dtype=DB1_kpca_desc),
                                title='Kmer signature PCAs',
                                expectedrows=num_cons
                                )
                     
        # update the formatVersion field and we're done
        DB1_meta_desc = [('stoitColNames', '|S512'),
                         ('numStoits', int),
                         ('merColNames', '|S4096'),
                         ('merSize', int),
                         ('numMers', int),
                         ('numCons', int),
                         ('numBins', int),
                         ('clustered', bool),
                         ('complete', bool),
                         ('formatVersion', int)
                         ]
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta[0]        
        
            meta_data = (meta["stoitColNames"],
                         meta["numStoits"],
                         meta["merColNames"],
                         meta["merSize"],
                         meta["numMers"],
                         meta["numCons"],
                         meta["numBins"],
                         meta["clustered"],
                         meta["complete"],
                         1) # ensure formatVersion field exists
            meta = np.array([meta_data], dtype=DB1_meta_desc)
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1)
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"

    def upgradeDB_1_to_2(self, dbFileName):
        """Upgrade a GM db from version 1 to version 2"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 1 to version 2 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving a variable number of kmerSig PCA's
        # and GC information for each contig
        print "    Calculating and storing the kmer signature PCAs"

        # grab any data needed from database before opening if for modification
        bin_ids = self.getBins(dbFileName)
        orig_con_names = self.getContigNames(dbFileName)

        # compute the PCA of the ksigs
        conParser = ContigParser()
        reader = FastaReader()
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = _DB1_PCAKsigs(ksigs)
        num_cons = len(pc_ksigs)
        DB2_kpca_desc = [('pc%d' % (i+1), float) for i in range(len(pc_ksigs[0]))]
        kpca_data = np.array(pc_ksigs, dtype=DB2_kpca_desc)
         
        # Add GC
        contigFile = raw_input('\nPlease specify fasta file containing the bam reference sequences: ')
        with open(contigFile, "r") as f:
            try:
                contigInfo = {}
                for cid,seq in reader.readFasta(f):
                    contigInfo[cid] = (len(seq), conParser.calculateGC(seq))

                # sort the contig names here once!
                con_names = np.array(sorted(contigInfo.keys()))

                # keep everything in order...
                con_gcs = np.array([contigInfo[cid][1] for cid in con_names])
                con_lengths = np.array([contigInfo[cid][0] for cid in con_names])
            except:
                print "Error parsing contigs"
                raise

        # remove any contigs not in the current DB (these were removed due to having zero coverage)
        good_indices = [i for i in range(len(orig_con_names)) if orig_con_names[i] in con_names]

        con_names = con_names[good_indices]
        con_lengths = con_lengths[good_indices]
        con_gcs = con_gcs[good_indices]
        bin_ids = bin_ids[good_indices]

        DB2_contigs_desc = [('cid', '|S512'),
                            ('bid', int),
                            ('length', int),
                            ('gc', int)]
        contigs_data = np.array([zip(con_names,
                                 bin_ids,
                                 con_lengths,
                                 con_gcs)],
                                dtype=DB2_contigs_desc)
        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            profile_group = h5file.get_node('/', name='profile')
            try:
                h5file.remove_node(profile_group, 'tmp_kpca')
            except:
                pass
            h5file.create_table(profile_group,
                                'tmp_kpca',
                                kpca_data,
                                title='Kmer signature PCAs',
                                expectedrows=num_cons
                                )
            
            meta_group = h5file.get_node('/', name='meta')
            try:
                h5file.remove_node(meta_group, "tmp_contigs")
            except:
                pass
            h5file.createTable(meta_group,
                               "tmp_contigs",
                               contigs_data,
                               title='Contig information',
                               expectedrows=num_cons
                               )
                
            h5file.rename_node(profile_group, 'kpca', 'tmp_kpca', overwrite=True)
            h5file.rename_node(meta_group, 'contigs', 'tmp_contigs', overwrite=True)

        # update the formatVersion field and we're done
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta.read()
            meta[0]["formatVersion"] = 2
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1)
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"

    def upgradeDB_2_to_3(self, dbFileName):
        """Upgrade a GM db from version 2 to version 3"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 2 to version 3 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the variance for each kmerSig PCA
        print "    Calculating and storing variance of kmer signature PCAs"

        # compute the PCA of the ksigs
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = _DB1_PCAKsigs(ksigs)

        # calcualte variance of each PC
        pc_var = [sumvariance[0]]
        for i in xrange(1, len(sumvariance)):
          pc_var.append(sumvariance[i]-sumvariance[i-1])
        pc_var = tuple(pc_var)

        DB3_kpca_variance_desc = [('pc%d_var' % (i+1), float) for i in range(len(pc_var))]
        kpca_variance_data = np.array([pc_var], dtype=DB3_kpca_variance_desc)

        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            meta = h5file.get_node('/', name='meta')
            try:
                h5file.remove_node(meta, 'tmp_kpca_variance')
            except:
                pass

            h5file.create_table(meta,
                                'tmp_kpca_variance',
                                kpca_variance_data,
                                title='Variance of kmer signature PCAs',
                                expectedrows=1
                                )

            h5file.rename_node(meta, 'kpca_variance', 'tmp_kpca_variance', overwrite=True)

        # update the formatVersion field and we're done
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta.read()
            meta[0]["formatVersion"] = 3
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1)
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"

    def upgradeDB_3_to_4(self, dbFileName):
        """Upgrade a GM db from version 3 to version 4"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 3 to version 4 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be adding a chimeric flag for each bin
        print "    Adding chimeric flag for each bin."
        print "    !!! Groopm core must be run again for this flag to be properly set. !!!"

        # read existing data in 'bins' table
        with tables.open_file(dbFileName, mode='r') as h5file:
            all_rows = h5file.root.meta.bins.read()

        # write new table with chimeric flag set to False by default
        DB4_bin_desc = [('bid', int),
                        ('numMembers', int),
                        ('isLikelyChimeric', bool)]

        data = [(bid, num_members, False) for (bid, num_members) in all_rows]
        bin_data = np.array(data, dtype=DB4_bin_desc)

        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            meta_group = h5file.get_node('/', name='meta')

            try:
                h5file.remove_node(meta_group, 'tmp_bins')
            except:
                pass
                
            h5file.create_table(meta_group,
                                'tmp_bins',
                                bin_data,
                                title="Bin information",
                                expectedrows=1
                                )

            h5file.rename_node(meta_group, 'bins', 'tmp_bins', overwrite=True)

        # update the formatVersion field and we're done
        
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta.read()
            meta[0]["formatVersion"] = 4
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1
                                )
                                
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"

    def upgradeDB_4_to_5(self, dbFileName):
        """Upgrade a GM db from version 4 to version 5"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 4 to version 5 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the transformed coverage coords
        print "    Saving transformed coverage profiles"
        print "    You will not need to re-run parse or core due to this change"

        # we need to get the raw coverage profiles and the kmerPCA1 data
        raw_coverages = self.getCoverages(dbFileName)
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = _DB1_PCAKsigs(ksigs)
        kPCA_1 = pc_ksigs[:,0]
        norm_coverages = np.linalg.norm(raw_coverages, axis=1)

        CT = _DB4_CoverageTransformer(len(raw_coverages),
                                     self.getNumContigs(dbFileName),
                                     norm_coverages,
                                     kPCA_1,
                                     raw_coverages,
                                     self.getCovColNames(dbFileName))
        # now CT stores the transformed coverages and other important information
        # we will write this to the database
                                     
        # stoit col names may have been shuffled
        with tables.open_file(dbFileName, mode='r') as h5file:
            meta_data = h5file.root.meta.meta.read()
        meta_data[0]['stoitColNames'] = ",".join([str(i) for i in CT.stoitColNames])
        meta_data[0]['numStoits'] = CT.numStoits
        
        DB5_coverages_desc = [(col_name, float) for col_name in CT.stoitColNames]
        coverages_data = np.array(CT.covProfiles, dtype=DB5_coverages_desc)
        
        DB5_transCoverage_desc = [('x', float),
                                  ('y', float),
                                  ('z', float)]
        transCoverage_data = np.array(CT.transformedCP , dtype=DB5_transCoverage_desc)
        
        DB5_transCoverageCorners_desc = [('x', float),
                                         ('y', float),
                                         ('z', float)]
        transCoverageCorners_data = np.array(CT.corners, dtype=DB5_transCoverageCorners_desc)
                                         
        DB5_normCoverage_desc = [('normCov', float)]
        normCoverage_data = np.array(CT.normCoverages , dtype=DB5_normCoverage_desc)
        
        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            meta_group = h5file.get_node('/', name='meta')
            profile_group = h5file.get_node('/', name='profile')

            # raw coverages - we may have reordered rows, so we should fix this now!
            try:
                h5file.remove_node(profile_group, 'tmp_coverages')
            except:
                pass
            
            h5file.create_table(profile_group,
                                'tmp_coverages',
                                coverages_data,
                                title="Bam based coverage",
                                expectedrows=CT.numContigs
                                )
                
            # transformed coverages 
            h5file.create_table(profile_group,
                                'transCoverage',
                                transCoverage_data,
                                title="Transformed coverage",
                                expectedrows=CT.numContigs
                                )

            # normalised coverages
            h5file.create_table(profile_group,
                                'normCoverage',
                                normCoverage_data,
                                title="Normalised coverage",
                                expectedrows=CT.numContigs
                                )

            # transformed coverage corners
            h5file.create_table(meta_group,
                                'transCoverageCorners',
                                transCoverageCorners_data,
                                title="Transformed coverage corners",
                                expectedrows=CT.numStoits
                                )
                               
            # metadata            
            try:
                h5file.remove_node(meta_group, 'tmp_meta')
            except:
                pass
            
            h5file.create_table(meta_group,
                                "tmp_meta",
                                meta_data,
                                title="Descriptive data",
                                expectedrows=1
                                )

                
            h5file.rename_node(profile_group, "coverage", "tmp_coverages", overwrite=True)
            h5file.rename_node(meta_group, "meta", "tmp_meta", overwrite=True)

        # update the formatVersion field and we're done
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta.read()
            meta[0]["formatVersion"] = 5
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
                
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1
                                )
                                
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"
        
    def upgradeDB_5_to_6(self, dbFileName):
        """Upgrade a GM db from version 5 to version 6"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 5 to version 6 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the changes in this version are as follows:
        #   delete profiles/kpca table
        #   delete profiles/tranCoverage table
        #   delete meta/kpca_variance table
        #   delete meta/transCoverageCorners table
        #   new group mappings
        #   new table mappings/mappings
        #   new table mappings/classification
        #   new table meta/markers
        #   new table meta/taxons
        #   new meta/meta table columns: 'numMarkers'
        print "    Storing marker hits"
        print "    Re-run core to get better bins"

        cfe = ClassificationEngine()
        mapper = Mapper(graftm_package_list=[])
        
        # contig distances
        cov_profiles = self.getCoverages(dbFileName)
        con_ksigs = self.getKmerSigs(dbFileName)
        con_lengths = self.getContigLengths(dbFileName)
        num_cons = len(con_lengths)
        
        # mappings
        contig_file = raw_input('\nPlease specify fasta file containing the bam reference sequences: ')
        con_names = self.getContigNames(dbFileName)
        cid2Indices = dict(zip(con_names, range(len(con_names))))
        (contig_indices, marker_indices, marker_names, marker_counts, taxstrings) = mapper.getMappings(contig_file, cid2Indices)
        (tax_table, taxon_names) = cfe.parse(taxstrings)
        num_mappings = len(contig_indices)
        num_markers = len(marker_names)
                                         
        DB6_mappings_desc = self.mappings_desc
        mappings_data = np.array(zip(marker_indices, contig_indices, taxstrings), dtype=DB6_mappings_desc)
        
        DB6_classification_desc = self.classification_desc
        classification_data = np.array([tuple(i) for i in tax_table], dtype=DB6_classification_desc)
        
        DB6_reachability_desc = self.reachability_desc
        reachability_data = np.array([], dtype=DB6_reachability_desc)
        
        DB6_markers_desc = self.markers_desc
        markers_data = np.array(zip(marker_names, marker_counts), dtype=DB6_markers_desc)
        
        DB6_taxons_desc = self.taxons_desc
        taxons_data = np.array([taxon_names], dtype=DB6_taxons_desc)
            
        # metadata
        with tables.open_file(dbFileName, mode='r', root_uep="/") as h5file:
            meta = h5file.root.meta.meta[0]
        DB6_meta_desc = self.meta_desc
        meta_data = np.array([(
            meta['stoitColNames'],
            meta['numStoits'],
            meta['merColNames'],
            meta['merSize'],
            meta['numMers'],
            meta['numCons'],
            meta['numBins'],
            num_markers,
            meta['clustered'],
            meta['complete'],
            meta['formatVersion']
            )],
            dtype=DB6_meta_desc)
        
        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            mappings_group = h5file.create_group("/", "mappings", "Contig mappings")
            meta_group = h5file.get_node("/", "meta")
            profile_group = h5file.get_node("/", "profile")
                
            # mappings
            h5file.create_table(mappings_group,
                                'mappings',
                                mappings_data,
                                title="Marker mappings",
                                expectedrows=num_mappings
                                )
                                
            # classifications
            h5file.create_table(mappings_group,
                                "classification",
                                classification_data,
                                title="Mapping classifications",
                                expectedrows=num_mappings
                                )
                                
                                    
            #reachability
            h5file.create_table(meta_group,
                                'reachability',
                                reachability_data,
                                title="Reachability ordering",
                                expectedrows=1
                                )
                                
            # markers
            h5file.create_table(meta_group,
                                "markers",
                                markers_data,
                                title="Marker information",
                                expectedrows=num_markers
                                )
            
            # taxons
            h5file.create_table(meta_group,
                                "taxons",
                                taxons_data,
                                title="Taxon information",
                                expectedrows=len(taxon_names)
                                )
                                
            # update metadata
            try:
                h5file.remove_node(meta_group, "tmp_meta")
            except:
                pass
                
            h5file.create_table(meta_group,
                                "tmp_meta",
                                meta_data,
                                title="Descriptive data",
                                expectedrows=1
                                )
                                
            h5file.rename_node(meta_group, "meta", "tmp_meta", overwrite=True)
            
            # remove old tables
            try:
                h5file.remove_node(profile_group, "kpca")
            except:
                pass
            try:
                h5file.remove_node(profile_group, "transCoverage")
            except:
                pass
            try:
                h5file.remove_node(meta_group, "kpca_variance")
            except:
                pass
            try:
                h5file.remove_node(meta_group, "transCoverageCorners")
            except:
                pass
            
        # update the formatVersion field and we're done
        
        with tables.open_file(dbFileName, mode='a', root_uep="/meta") as h5file:
            meta = h5file.root.meta.read()
            meta[0]["formatVersion"] = 6
            try:
                h5file.remove_node("/", "tmp_meta")
            except:
                pass
                
            h5file.create_table("/",
                                "tmp_meta",
                                meta,
                                title="Descriptive data",
                                expectedrows=1
                                )
                                
            h5file.rename_node("/", "meta", "tmp_meta", overwrite=True)
        print "*******************************************************************************"

#------------------------------------------------------------------------------
# GET TABLES - GENERIC
            
    def iterrows(self, table, rows):
        """iterate selected rows of table"""
        if(len(rows) != 0):
            return (table[x] for x in rows)
        else:
            return (x.fetch_all_fields() for x in table)
            
#------------------------------------------------------------------------------
# GET TABLES - PROFILES

    def getKmerSigs(self, dbFileName, indices=[]):
        """Load columns from kmer sig profile"""
        with tables.open_file(dbFileName, 'r', root_uep='/profile') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file.root.kms, indices)])
        
    def getCoverages(self, dbFileName, indices=[]):
        """Load columns from coverage profile"""
        with tables.open_file(dbFileName, 'r', root_uep='/profile') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file.root.coverage, indices)])
        
    def getNormCoverages(self, dbFileName, indices=[]):
        """Load columns for coverage norms"""
        with tables.open_file(dbFileName, 'r', root_uep='/profile') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file.root.normCoverage, indices)])

#------------------------------------------------------------------------------
# GET TABLES - MAPPINGS

    def getMappingContigs(self, dbFileName):
        """Load mapping contig indices"""
        with tables.open_file(dbFileName, "r", root_uep="/mappings") as h5file:
            return np.array([x for x in h5file.root.mappings.cols.contig])
            
    def getMappingMarkers(self, dbFileName):
        """Load mapping marker ids"""
        with tables.open_file(dbFileName, "r", root_uep="/mappings") as h5file:
            return np.array([x for x in h5file.root.mappings.cols.marker])
            
    def getMappingTaxstrings(self, dbFileName):
        """Load mapping contig indices"""
        with tables.open_file(dbFileName, "r", root_uep="/mappings") as h5file:
            return np.array([x for x in h5file.root.mappings.cols.taxstring])
            
    def getClassification(self, dbFileName):
        """Load classification table"""
        with tables.open_file(dbFileName, "r", root_uep="/mappings") as h5file:
            return np.array([list(x.fetch_all_fields()) for x in h5file.root.classification])
           
#------------------------------------------------------------------------------
# GET LINKS

    def restoreLinks(self, dbFileName, indices=[]):
        """Restore the links hash for a given set of indices"""
        with tables.open_file(dbFileName, 'r', root_uep="/links") as h5file:
            full_record = [list(x) for x in h5file.links.where("contig1 >= 0")]
        if indices == []:
            # get all!
            indices = self.getConditionalIndices(dbFileName)

        links_hash = {}
        if full_record != []:
            for record in full_record:
                # make sure we have storage
                if record[0] in indices and record[1] in indices:
                    try:
                        links_hash[record[0]].append(record[1:])
                    except KeyError:
                        links_hash[record[0]] = [record[1:]]
        return links_hash
            
#------------------------------------------------------------------------------
# GET TABLES - CONTIGS

    def getConditionalIndices(self, dbFileName, condition):
        """return the indices into the db which meet the condition"""
        if('' == condition):
            condition = "cid != ''" # no condition breaks everything!
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x.nrow for x in h5file.root.contigs.where(condition)])

    def getContigNames(self, dbFileName, indices=[]):
        """Load contig names"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["cid"] for x in self.iterrows(h5file.root.contigs,  indices)])
        
    def getBins(self, dbFileName, indices=[]):
        """Load bin assignments"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["bid"] for x in self.iterrows(h5file.root.contigs,  indices)])

    def getContigLengths(self, dbFileName, indices=[]):
        """Load contig lengths"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["length"] for x in self.iterrows(h5file.root.contigs,  indices)])

    def getContigGCs(self, dbFileName, indices=[]):
        """Load contig gcs"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["gc"] for x in self.iterrows(h5file.root.contigs,  indices)])
                            
#------------------------------------------------------------------------------
# GET TABLES - BINS
       
    def getBinStats(self, dbFileName):
        """Load data from bins table

        Returns a dict of type:
        { bid : numMembers }
        """
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return dict([(x["bid"], x["numMembers"]) for x in h5file.root.bins])
            
#------------------------------------------------------------------------------
# GET TABLES - REACHABILITY

    def getReachabilityOrder(self, dbFileName):
        """Load reachability data
        
        Returns a tuple: (ordered_indices, distances)
        """
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            (indices, dists) = zip(*[(x["contig"], x["distance"]) for x in h5file.root.reachability])
        return (np.array(indices), np.array(dists))
        
#------------------------------------------------------------------------------
# GET TABLES - MARKERS

    def getMarkerNames(self, dbFileName, indices=[]):
        """Load marker names"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["markerid"] for x in self.iterrows(h5file.root.markers, indices)])
            
    def getMarkerStats(self, dbFileName):
        """Load data from markers table
        
        Returns a dict of type:
            { markerid: numMappings }
        """
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return dict([(x["markerid"], x["numMappings"]) for x in h5file.root.markers])

#------------------------------------------------------------------------------
# GET TABLES - TAXONS

    def getTaxonNames(self, dbFileName, indices=[]):
        """Load taxon names"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return np.array([x["taxonid"] for x in self.iterrows(h5file.root.taxons, indices)])
            
#------------------------------------------------------------------------------
# GET METADATA

    def _getMeta(self, dbFileName):
        """return the metadata table as a structured array"""
        with tables.open_file(dbFileName, 'r', root_uep="/meta") as h5file:
            return h5file.root.meta[0]

    def getGMDBFormat(self, dbFileName):
        """return the format version of this GM file"""
        # this guy needs to be a bit different to the other meta methods
        # becuase earlier versions of GM didn't include a format parameter
        try:
            this_DB_version = self._getMeta(dbFileName)['formatVersion']
        except IndexError:
            # which type of error will python throw? who knows
            this_DB_version = 0
        except ValueError:
            # this happens when an oldskool formatless DB is loaded
            this_DB_version = 0
        return this_DB_version

    def getNumStoits(self, dbFileName):
        """return the value of numStoits in the metadata tables"""
        return self._getMeta(dbFileName)['numStoits']

    def getMerColNames(self, dbFileName):
        """return the value of merColNames in the metadata tables"""
        return self._getMeta(dbFileName)['merColNames']

    def getMerSize(self, dbFileName):
        """return the value of merSize in the metadata tables"""
        return self._getMeta(dbFileName)['merSize']

    def getNumMers(self, dbFileName):
        """return the value of numMers in the metadata tables"""
        return self._getMeta(dbFileName)['numMers']

    def getNumContigs(self, dbFileName):
        """return the value of numCons in the metadata tables"""
        return self._getMeta(dbFileName)['numCons']

    def getNumBins(self, dbFileName):
        """return the value of numBins in the metadata tables"""
        return self._getMeta(dbFileName)['numBins']

    def getCovColNames(self, dbFileName):
        """return the value of stoitColNames in the metadata tables"""
        return self._getMeta(dbFileName)['stoitColNames']

    def isClustered(self, dbFileName):
        """Has this data set been clustered?"""
        return self._getMeta(dbFileName)['clustered']

    def isComplete(self, dbFileName):
        """Has this data set been *completely* clustered?"""
        return self._getMeta(dbFileName)['complete']
            
#------------------------------------------------------------------------------
#  SET OPERATIONS - UPDATE BINS  
        
    def setBinAssignments(self, dbFileName, updates={}, nuke=False):
        """Set per-contig bins

        updates is a dictionary which looks like:
        { tableRow : bid }
        """
        
        # get the contigs table image
        with tables.open_file(dbFileName, mode='r', root_uep='/meta') as h5file:
            if nuke:
                (con_names, con_lengths, con_gcs) = zip(*[(x["cid"], x["length"], x["gc"]) for x in h5file.root.contigs])
                num_cons = len(con_lengths)
                # clear all bin assignments
                bins = [0]*num_cons
            else:
                (con_names, bins, con_lengths, con_gcs) = zip(*[tuple(x) for x in h5file.root.contigs])
        
        # now apply the updates
        for tr in updates.keys():
            bins[tr] = updates[tr]

        # build the new contigs table image
        contigs_data = np.array(zip(con_names, bins, con_lengths, con_gcs),
                                dtype=self.contigs_desc)
        
        # build the new bins table image
        (bids, num_members) = np.unique(bins, return_counts=True)
        updates = [(bid, num_members, False) for (bid, num_members) in zip(bids, num_members)] #isLikelyChimeric is always false
        bins_data = np.array(updates, dtype=self.bins_desc)
        
        # update num bins metadata
        num_bins = len(bids) - int(0 in bids)
        meta = self._getMeta(dbFileName)
        meta['numBins'] = num_bins  
        if num_bins > 0:
            meta['clustered'] = True
        meta_data = np.array([meta], dtype=self.meta_desc)
                                
          
        # Let's do the update atomically... 
        with tables.open_file(dbFileName, mode='a', root_uep='/meta') as h5file:
            
            try:
                # get rid of any failed attempts
                h5file.remove_node('/', 'tmp_contigs')
            except:
                pass
            h5file.create_table('/',
                                'tmp_contigs',
                                contigs_data,
                                title="Contig information",
                                expectedrows=num_cons)
                
            # update bin table
            try:
                h5file.remove_node(meta_group, 'tmp_bins')
            except:
                pass

            h5file.create_table('/',
                                'tmp_bins',
                                bins_data,
                                title="Bin information",
                                expectedrows=len(bids))
                
            # update meta table
            try:
                h5file.remove_node(meta_group, 'tmp_meta')
            except:
                pass
                
            h5file.create_table('/',
                                'tmp_meta',
                                meta_data,
                                title="Descriptive data",
                                expectedrows=1)

            # rename the tmp tables to overwrite
            h5file.rename_node("/", 'contigs', 'tmp_contigs', overwrite=True)
            h5file.rename_node("/", 'bins', 'tmp_bins', overwrite=True)
            h5file.rename_node("/", 'meta', 'tmp_meta', overwrite=True)
            
    def nukeBins(self, dbFileName):
        """Reset all bin information, completely"""
        print "    Clearing all old bin information from",dbFileName
        self.setBinAssignments(dbFileName, updates={}, nuke=True)
        
#------------------------------------------------------------------------------
#  SET OPERATIONS - REACHABILITY
        
    def setReachabilityOrder(self, dbFileName, updates=[]):
        """Set per-contig reachability

        updates is a list of (contig, distance) pairs in reachability order
        """
        
        # build the new reachability table image
        reachability_data = np.array(updates,
                                     dtype=self.reachability_desc)
          
        # Update database 
        with tables.open_file(dbFileName, mode='a', root_uep='/meta') as h5file:
            
            try:
                # get rid of any failed attempts
                h5file.remove_node('/', 'tmp_reachability')
            except:
                pass
                
            h5file.create_table('/',
                                'tmp_reachability',
                                reachability_data,
                                title="Reachability ordering",
                                expectedrows=len(updates))

            # rename the tmp tables to overwrite
            h5file.rename_node("/", 'reachability', 'tmp_reachability', overwrite=True)

#------------------------------------------------------------------------------
# FILE / IO

    def dumpData(self, dbFileName, fields, outFile, separator, useHeaders):
        """Dump data to file"""
        header_strings = []
        data_arrays = []
        num_fields = len(fields)
        data_converters = []

        try:
            for field in fields:
                if field == 'names':
                    header_strings.append('cid')
                    data_arrays.append(self.getContigNames(dbFileName))
                    data_converters.append(lambda x : x)

                elif field == 'sizes':
                    header_strings.append('size')
                    data_arrays.append(self.getContigLengths(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'gc':
                    header_strings.append('GC%')
                    data_arrays.append(self.getContigGCs(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'bins':
                    header_strings.append('bid')
                    data_arrays.append(self.getBins(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'coverage':
                    stoits = self.getCovColNames(dbFileName).split(',')
                    for stoit in stoits:
                        header_strings.append(stoit)
                    data_arrays.append(self.getCoverages(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))
                    
                elif field == 'ncoverage':
                    header_strings.append('normCoverage')
                    data_arrays.append(self.getNormCoverages(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))

                elif field == 'mers':
                    mers = self.getMerColNames(dbFileName).split(',')
                    for mer in mers:
                        header_strings.append(mer)
                    data_arrays.append(self.getKmerSigs(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))
        except:
            print "Error when reading DB:", dbFileName, sys.exc_info()[0]
            raise

        try:
            with open(outFile, 'w') as fh:
                if useHeaders:
                    header = separator.join(header_strings) + "\n"
                    fh.write(header)

                num_rows = len(data_arrays[0])
                for i in range(num_rows):
                    fh.write(data_converters[0](data_arrays[0][i]))
                    for j in range(1, num_fields):
                        fh.write(separator+data_converters[j](data_arrays[j][i]))
                    fh.write('\n')
        except:
            print "Error opening output file %s for writing" % outFile
            raise
            
            
    def dumpMarkers(self, dbFileName, fields, outFile, separator, useHeaders):
        """Dump data to file"""
        header_strings = []
        data_arrays = []
        num_fields = len(fields)
        data_converters = []

        try:
            for field in fields:
                if field == 'contigs':
                    header_strings.append('cid')
                    data_arrays.append(self.getContigNames(dbFileName, self.getMappingContigs(dbFileName)))
                    data_converters.append(lambda x : x)

                elif field == 'markers':
                    header_strings.append('marker')
                    data_arrays.append(self.getMarkerNames(dbFileName, self.getMappingMarkers(dbFileName)))
                    data_converters.append(lambda x : x)

                elif field == 'taxstrings':
                    header_strings.append('taxonomy')
                    data_arrays.append(self.getMappingTaxstrings(dbFileName))
                    data_converters.append(lambda x : x)

        except:
            print "Error when reading DB:", dbFileName, sys.exc_info()[0]
            raise

        try:
            with open(outFile, 'w') as fh:
                if useHeaders:
                    header = separator.join(header_strings) + "\n"
                    fh.write(header)

                num_rows = len(data_arrays[0])
                for i in range(num_rows):
                    fh.write(data_converters[0](data_arrays[0][i]))
                    for j in range(1, num_fields):
                        fh.write(separator+data_converters[j](data_arrays[j][i]))
                    fh.write('\n')
        except:
            print "Error opening output file %s for writing" % outFile
            raise

      
#------------------------------------------------------------------------------
# Helpers

def _get_bam_descriptor(fullPath, index_num):
    """AUX: Reduce a full path to just the file name minus extension"""
    return str(index_num) + '_' + op_splitext(op_basename(fullPath))[0]
    
def _DB1_PCAKsigs(ksigs):
    # stub pca calculation
    return (ksigs[:, :2], np.zeros(len(ksigs)))
    
class _DB4_CoverageTransformer:
    # stup coverage transformation
    def __init__(self,
                 numContigs,
                 numStoits,
                 normCoverages,
                 kmerNormPC1,
                 coverageProfiles,
                 stoitColNames,
                 scaleFactor=1000):
        self.numContigs = numContigs
        self.numStoits = numStoits
        self.normCoverages = normCoverages
        self.kmerNormPC1 = kmerNormPC1
        self.covProfiles = coverageProfiles
        self.stoitColNames = np.array(stoitColNames.split(','))
        self.indices = range(self.numContigs)
        self.scaleFactor = scaleFactor
        
        self.TCentre = None
        self.transformedCP = np.zeros((numContigs, 3))
        self.corners = np.zeros((numStoits, 3))
            
            
###############################################################################
###############################################################################
###############################################################################
###############################################################################

class ContigParser:
    """Main class for reading in and parsing contigs"""
    
    def parse(self, contigFile, cutoff, kse):
        """Do the heavy lifting of parsing"""
        print "Parsing contigs"
        contigInfo = {} # save everything here first so we can sort accordingly
        reader = FastaReader()
        for cid,seq in reader.readFasta(contigFile):
            if len(seq) >= cutoff:
                try:
                    gc = self.calculateGC(seq)
                except ZeroDivisionError:
                    print "***WARNING*** Using 0.5 as GC percentage of sequence '%s' " % seq
                    gc = 0.5
                contigInfo[cid] = (kse.getKSig(seq.upper()), len(seq), gc)

        # sort the contig names here once!
        con_names = np.array(sorted(contigInfo.keys()))

        # keep everything in order...
        con_gcs = np.array([contigInfo[cid][2] for cid in con_names])
        con_lengths = np.array([contigInfo[cid][1] for cid in con_names])
        con_ksigs = np.array([contigInfo[cid][0] for cid in con_names])

        return (con_names, con_gcs, con_lengths, con_ksigs)

    def calculateGC(self, seq):
      """Calculate fraction of nucleotides that are G or C."""
      testSeq = seq.upper()
      gc = testSeq.count('G') + testSeq.count('C')
      at = testSeq.count('A') + testSeq.count('T')

      return float(gc) / (gc + at)

    def getWantedSeqs(self, contigFile, wanted, out_dict):
        """Do the heavy lifting of parsing"""
        print "Parsing contigs"
        reader = FastaReader()
        for cid,seq in reader.readFasta(contigFile):
            if(cid in wanted):
                out_dict[cid] = seq

        
###############################################################################
###############################################################################
###############################################################################
###############################################################################

class KmerSigEngine:
    """Simple class for determining kmer signatures"""
    
    compl = s_maketrans('ACGT', 'TGCA')
    
    def __init__(self, kLen=4):
        self.kLen = kLen
        (self.kmerCols, self.llDict) = self.makeKmerColNames(makeLL=True)
        self.numMers = len(self.kmerCols)
        
    def calculateGCVector(self):
        return [float(gc)/(gc+at) for (gc, at) in ((mer.count('G')+mer.count('C'), mer.count('A')+mer.count('T')) for mer in self.kmerCols)]

    def makeKmerColNames(self, makeLL=False):
        """Work out the range of kmers required based on kmer length

        returns a list of sorted kmers and optionally a llo dict
        """
        # build up the big list
        base_words = ("A","C","G","T")
        out_list = ["A","C","G","T"]
        for i in range(1,self.kLen):
            working_list = []
            for mer in out_list:
                for char in base_words:
                    working_list.append(mer+char)
            out_list = working_list

        # pare it down based on lexicographical ordering
        ret_list = []
        ll_dict = {}
        for mer in out_list:
            lmer = self.shiftLowLexi(mer)
            ll_dict[mer] = lmer
            if lmer not in ret_list:
                ret_list.append(lmer)
        if makeLL:
            return (sorted(ret_list), ll_dict)
        else:
            return sorted(ret_list)

    def getGC(self, seq):
        """Get the GC of a sequence"""
        Ns = seq.count('N') + seq.count('n')
        compl = s_maketrans('ACGTacgtnN', '0110011000')
        return sum([float(x) for x in list(seq.translate(compl))])/float(len(seq) - Ns)

    def shiftLowLexi(self, seq):
        """Return the lexicographically lowest form of this sequence"""
        # build a dictionary to know what letter to switch to
        rseq = seq.translate(self.compl)[::-1]
        if(seq < rseq):
            return seq
        return rseq

    def getKSig(self, seq):
        """Work out kmer signature for a nucleotide sequence

        returns a tuple of floats which is the kmer sig
        """
        # tmp storage
        sig = dict(zip(self.kmerCols, [0.0] * self.numMers))
        # the number fo kmers in this sequence
        num_mers = len(seq)-self.kLen+1
        for i in range(0,num_mers):
            try:
                sig[self.llDict[seq[i:i+self.kLen]]] += 1.0
            except KeyError:
                # typically due to an N in the sequence. Reduce the number of mers we've seen
                num_mers -= 1

        # normalise by length and return
        try:
            return tuple([sig[x] / num_mers for x in self.kmerCols])
        except ZeroDivisionError:
            print "***WARNING*** Sequence '%s' is not playing well with the kmer signature engine " % seq
            return tuple([0.0] * self.numMers)
        
            
###############################################################################
###############################################################################
###############################################################################
###############################################################################

class BamParser:
    """Parse multiple bam files and write the output to hdf5 """
    def parse(self, bamFiles, contigNames, cid2Indices, threads):
        """Parse multiple bam files and store the results in the main DB"""
        print "Parsing BAM files using %d threads" % threads

        BP = BMBP(BMCT(CT.P_MEAN_TRIMMED, 5, 5))
        BP.parseBams(bamFiles,
                     doLinks=False,
                     doCovs=True,
                     threads=threads,
                     verbose=True)

        # we need to make sure that the ordering of contig names is consistent
        # first we get a dict that connects a contig name to the index in
        # the coverages array
        con_name_lookup = dict(zip(BP.BFI.contigNames,
                                   range(len(BP.BFI.contigNames))))

        # Next we build the cov_sigs array by appending the coverage
        # profiles in the same order. We need to handle the case where
        # there is no applicable contig in the BamM-derived coverages
        cov_sigs = []
        for cid in contigNames:
            try:
                cov_sigs.append(tuple(BP.BFI.coverages[con_name_lookup[cid]]))
            except KeyError:
                # when a contig is missing from the BAM we just give it 0
                # coverage. It will be removed later with a warning then
                cov_sigs.append(tuple([0.]*len(bamFiles)))

        #######################################################################
        # LINKS ARE DISABLED UNTIL STOREM COMES ONLINE
        #######################################################################
        # transform the links into something a little easier to parse later
        rowwise_links = []
        if False:
            for cid in links:
                for link in links[cid]:
                    try:
                        rowwise_links.append((cid2Indices[cid],     # contig 1
                                              cid2Indices[link[0]], # contig 2
                                              int(link[1]),         # numReads
                                              int(link[2]),         # linkType
                                              int(link[3])          # gap
                                              ))
                    except KeyError:
                        pass

        return ([BP.BFI.bamFiles[i].fileName for i in range(len(bamFiles))],
                rowwise_links,
                np.array(cov_sigs))

    
###############################################################################
###############################################################################
###############################################################################
###############################################################################

class Mapper:
    """Calculate gene mappings using external mapper."""
    
    def __init__(self, working_directory=None, graftm_package_list=None, marker_file=None):
        self._working_directory = working_directory
        self._marker_file = marker_file
        if self._marker_file is not None:
            self._mode = "file"
        elif graftm_package_list is not None:
            self._graftm_package_list = graftm_package_list
            self._mode = "graftm"
        else:
            self._mode = "singlem"
        
    def _runMapper(self, contig_file, cid_2_indices, mode, working_directory):
        if mode=="graftm":
            mapper = GraftMMapper(working_directory, self._graftm_package_list, silent=True)
        elif mode=="singlem":
            mapper = SingleMMapper(working_directory, silent=True)
        else:
            raise ValueError("Invalid argument paramter 'mode': '%s'"  % mode)
        return mapper.getMappings(contig_file, cid_2_indices)
        
    def getMappings(self, contig_file, cid_2_indices):
        print "Mapping contigs"
        if self._mode=="file":
            mapper = MappingParser()
            with open(self._marker_file, "r") as f:
                try:
                    (con_indices, map_markers, map_taxstrings) = mapper.parse(f, cid_2_indices)
                except:
                    print "Error parsing mappings"
                    raise
        
        working_directory = self._working_directory
        if working_directory is None:
            tmp = tempdir.TempDir()
            working_directory = tmp.name
            (con_indices, map_markers, map_taxstrings) = self._runMapper(contig_file, cid_2_indices, self._mode, working_directory)
            tmp.dissolve()
        else:
            (con_indices, map_markers, map_taxstrings) = self._runMapper(contig_file, cid_2_indices, self._mode, working_directory)
            
        con_indices = np.array(con_indices);
        map_markers = np.array(map_markers);
        map_taxstrings = np.array(map_taxstrings);
        (marker_names, marker_indices, marker_counts) = np.unique(map_markers, return_inverse=True, return_counts=True)
        return (con_indices, marker_indices, marker_names, marker_counts, map_taxstrings)
        
        
class MappingParser:
    """Read a file of tab delimited contig names, marker names and optionally classifications."""
    def parse(self, fp, cid2Indices):
        """Do the heavy lifting of parsing"""
        print "Parsing mappings"
        contig_indices = []
        map_markers = []
        map_taxstrings = []
        
        reader = CSVReader()
        for l in reader.readCSV(fp, "\t"):
            try:
                contig_index = cid2Indices[l[0]]
            except:
                continue
            
            contig_indices.append(contig_index)
            map_markers.append(l[1])
            try:
                map_taxstrings.append(l[2])
            except IndexError:
                map_taxstrings.append("")
                
        return (contig_indices, map_markers, map_taxstrings)

###############################################################################
###############################################################################
###############################################################################
###############################################################################

class ClassificationEngine:
    TAGS = ['d__', 'p__', 'c__', 'o__', 'f__', 'g__', 's__']
    
    def parse(self, taxstrings):
        """
        Parameters
        ----------
        taxstrings: sequence of strings
        
        Returns
        -------
        table: ndarray
            n-by-7 array where n is the number of mappings. `table[i]` contains
            indices into the `taxons` array corresponding to the taxon with the
            corresponding ranks for each column:
                0 - Domain
                1 - Phylum
                2 - Class
                3 - Order
                4 - Family
                5 - Genus
                6 - Species
        
        taxons: ndarray
            Array of taxonomic classification strings.
        """
        print "Parsing taxstrings"
        n = len(taxstrings)
        taxon_dict = { "": 1 }
        counter = 1
        table = np.zeros((n, len(self.TAGS)), dtype=int)
        for (i, s) in enumerate(taxstrings):
            for (j, rank) in enumerate(self.parse_taxstring(s)):
                try:
                    table[i, j] = taxon_dict[rank]
                except KeyError:
                    counter += 1
                    table[i, j] = counter
                    taxon_dict[rank] = counter
        
        taxons = np.concatenate(([""], taxon_dict.keys()))
        taxons[taxon_dict.values()] = taxons[1:].copy()
        
        return (table, taxons)
        
    def parse_taxstring(self, taxstring):
        fields = [field.strip() for field in  taxstring.split(';')]
        if fields[0] =="Root":
            fields = fields[1:]
        ranks = []
        bad_format = []
        try:
            for (string, prefix) in zip(fields, self.TAGS):
                if string=='': break
                if string.startswith(prefix):
                    string = string[len(prefix):]
                else:
                    for bad_prefix in self.TAGS:
                        if string.startswith(bad_prefix):
                            raise BadTaxonomicStringException("Warning: Expected `{0}` prefix but encountered `{1}`. ".format(prefix, bad_prefix))
                    bad_format.append(prefix)
                ranks.append(string)
        except BadTaxonomicStringException as e:
            print(e, '. Dropping remaining fields.')
        if len(bad_format) >= 1:
            print("Warning: Missing prefix(es): `{0}` when parsing taxstring: `{1}`. Defaulting to assigning taxonomic ranks by position.".format('`, `'.join(bad_format), taxstring))
        return ranks
        
    def getDistance(self, a, b):
        for (d, s, o) in zip(range(7, 0, -1), a, b):
            # 0 = untagged at current level (assume coherent with any tag)
            # 1 = empty tag at current level (assume incoherent with other empty and non-empty tags)
            if s==0 or o==0:
                break
            if s==1 or o==1 or s!=o:
                return d
        return 0
        
    def isPrefix(self, a, b):
        # 0 = untagged at current level (assume coherent with any tag)
        # 1 = empty tag at current level (assume incoherent with other empty and non-empty tags)
        for (s, o) in zip(a, b):
            if s==0 or o==0:
                break
            if s==1 or o==1 or s!=0:
                return False
        return True

    
###############################################################################
###############################################################################
###############################################################################
############################################################################### 
