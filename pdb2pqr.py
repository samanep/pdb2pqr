#!/usr/bin/python2 -O

"""
    Driver for PDB2PQR

    This module takes a PDB file as input and performs optimizations
    before yielding a new PDB-style file as output.

    Ported to Python by Todd Dolinsky (todd@ccb.wustl.edu)
    Washington University in St. Louis

    Parsing utilities provided by Nathan A. Baker (baker@biochem.wustl.edu)
    Washington University in St. Louis
"""

__date__ = "14 April 2004"
__author__ = "Todd Dolinsky, Nathan Baker"

import string
import sys
import getopt
import os
import time
from pdb import *
from utilities import *
from structures import *
from definitions import *
from forcefield import *
from routines import *
from protein import *
from StringIO import *
from server import *


def usage(rc):
    """
        Print usage for this script to stdout.

        Parameters
            rc:  Exit status (int)
    """

    str = "\n"
    str = str + "pdb2pqr\n"
    str = str + "\n"
    str = str + "This module takes a PDB file as input and performs\n"
    str = str + "optimizations before yielding a new PDB-style file as\n"
    str = str + "output\n"
    str = str + "\n"
    str = str + "Usage: pdb2pqr.py [options] --ff=<forcefield> <path> [output-path]\n"
    str = str + "    Required Arguments:\n"
    str = str + "        <path>        :  The path to the PDB file or an ID\n"
    str = str + "                         to obtain from the PDB archive\n"
    str = str + "        <forcefield>  :  The forcefield to use - currently\n"
    str = str + "                         amber, charmm, and parse are supported.\n"
    str = str + "    Optional Arguments:\n"
    str = str + "        --nodebump    :  Do not perform the debumping operation\n"
    str = str + "        --nohopt      :  Do not perform hydrogen optimization\n"
    str = str + "        --nohdebump   :  Do not perform hydrogen debumping\n"
    str = str + "        --nowatopt    :  Do not perform water optimization\n"
    str = str + "        --verbose (-v):  Print information to stdout\n"
    str = str + "        --help    (-h):  Display the usage information\n"
    str = str + "    If no output-path is specified, the PQR file is\n"
    str = str + "    printed to stdout\n"
    str = str + "\n"
    sys.stderr.write(str)
    sys.exit(rc)

def printHeader(atomlist, reslist, charge, ff, warnings):
    """
        Print the header for the PQR file

        Parameters:
            atomlist: A list of atoms that were unable to have
                      charges assigned (list)
            reslist:  A list of residues with non-integral charges
                      (list)
            charge:   The total charge on the protein (float)
            ff:       The forcefield name (string)
            warnings: A list of warnings generated from routines (list)
        Returns
            header:   The header for the PQR file (string)
    """
    header = "REMARK   1 PQR file generated by PDB2PQR\n"
    header = header + "REMARK   1\n"
    header = header + "REMARK   1 Forcefield Used: %s\n" % ff
    header = header + "REMARK   1\n"

    for warning in warnings:
        header = header + "REMARK   5 " + warning 
    header = header + "REMARK   5\n"
    
    if len(atomlist) != 0:
        header += "REMARK   5 WARNING: PDB2PQR was unable to assign charges\n"
        header += "REMARK   5          to the following atoms (omitted below):\n"
        for atom in atomlist:
            header += "REMARK   5              %i %s in %s %i\n" % \
                      (atom.get("serial"), atom.get("name"), \
                       atom.get("residue").get("name"), \
                       atom.get("residue").get("resSeq"))
        header += "REMARK   5\n"
    if len(reslist) != 0:
        header += "REMARK   5 WARNING: Non-integral net charges were found in\n"
        header += "REMARK   5          the following residues:\n"
        for residue in reslist:
            header += "REMARK   5              %s %i - Residue Charge: %.4f\n" % \
                      (residue.get("name"), residue.get("resSeq"), \
                       residue.getCharge())
        header += "REMARK   5\n"
    header += "REMARK   6 Total charge on this protein: %.4f e\n" % charge
    header += "REMARK   6\n"

    return header
  
def runPDB2PQR(pdblist, verbose, ff, debump, hopt, hdebump, watopt):
    """
        Run the PDB2PQR Suite

        Parameters
            pdblist: The list of objects that was read from the PDB file
                     given as input (list)
            verbose: When 1, script will print information to stdout
                     When 0, no detailed information will be printed (int)
            ff:      The name of the forcefield (string)
            debump:  When 1, debump heavy atoms (int)
            hopt:    When 1, run hydrogen optimization (int)
            hdebump: When 1, debump hydrogens (int)
            watopt:  When 1, optimize water hydrogens (int)
        Returns
            header:  The PQR file header (string)
            lines:   The PQR file atoms (list)
    """
    lines = []
    
    start = time.time()

    if verbose:
        print "Beginning PDB2PQR...\n"

    myProtein = Protein(pdblist)
    if verbose:
        print "Created protein object -"
        print "\tNumber of residues in protein: %s" % myProtein.numResidues()
        print "\tNumber of atoms in protein   : %s" % myProtein.numAtoms()


    myDefinition = Definition()
    if verbose:
        print "Parsed Amino Acid definition file."


    myRoutines = Routines(myProtein, verbose, myDefinition)
    myRoutines.updateResidueTypes()
    myRoutines.updateSSbridges()
    myRoutines.updateExtraBonds()
    myRoutines.correctNames()

    # Don't do if AA not present
    
    myRoutines.findMissingHeavy()

    if debump:
        myRoutines.calculateChiangles()
        myRoutines.debumpProtein()  

    myRoutines.addHydrogens()

    if hopt:
        myRoutines.optimizeHydrogens()

    if watopt:
        if not hopt: myRoutines.optimizeHydrogens()
        myRoutines.optimizeWaters()
    else:
        myRoutines.randomizeWaters()


    if hdebump:
        myRoutines.calculateChiangles()
        myRoutines.debumpProtein()


    myForcefield = Forcefield(ff)
    hitlist, misslist = myRoutines.applyForcefield(myForcefield)
    reslist, charge = myProtein.getCharge()

    header = printHeader(misslist, reslist, charge, ff, myRoutines.getWarnings())
        
    lines = myProtein.printAtoms(hitlist)
    if verbose:
        print "Total time taken: %.2f seconds\n" % (time.time() - start)

    return header, lines

def mainCommand():
    """
        Main driver for running program from the command line.
    """
    shortOptlist = "h,v"
    longOptlist = ["help","verbose","ff=","nodebump","nohopt","nohdebump","nowatopt"]

    try: opts, args = getopt.getopt(sys.argv[1:], shortOptlist, longOptlist)
    except getopt.GetoptError, details:
        sys.stderr.write("GetoptError:  %s\n" % details)
        usage(2)

    if len(args) < 1 or len(args) > 2:
        sys.stderr.write("Incorrect number (%d) of arguments!\n" % len(args))
        usage(2)

    verbose = 0
    outpath = None
    ff = None
    debump = 1
    hopt = 1
    hdebump = 1
    watopt = 1
    for o,a in opts:
        if o in ("-v","--verbose"):
            verbose = 1
        elif o in ("-h","--help"):
            usage(2)
            sys.exit()
        elif o == "--nodebump":
            debump = 0
        elif o == "--nohopt":
            hopt = 0
        elif o == "--nohdebump":
            hdebump = 0
        elif o == "--nowatopt":
            watopt = 0
        elif o == "--ff":
            if a in ["amber","AMBER","charmm","CHARMM","parse","PARSE"]:
                ff = string.lower(a)
            else:
                raise ValueError, "Invalid forcefield %s!" % a

    if ff == None:
        raise ValueError, "Forcefield not specified!"
            
    path = args[0]
    file = getFile(path)
    pdblist, errlist = readPDB(file)
    
    if len(pdblist) == 0 and len(errlist) == 0:
        print "Unable to find file %s!\n" % path
        os.remove(path)
        sys.exit(2)

    if len(errlist) != 0 and verbose:
        print "Warning: %s is a non-standard PDB file.\n" % path
        print errlist

    header, lines = runPDB2PQR(pdblist, verbose, ff, debump, hopt, hdebump, watopt)

    if len(args) == 2:
        outpath = args[1]
        outfile = open(outpath,"w")
        outfile.write(header)
        for line in lines:
            outfile.write(line)
        outfile.close()
    else:
        print header
        for line in lines:
            print line

def mainCGI():
    """
        Main driver for running PDB2PQR from a web page
    """
    import cgi
    import cgitb

    cgitb.enable()
    form = cgi.FieldStorage()

    ff = form["FF"].value
    debump = 0
    hopt = 0
    input = 0
    hdebump = 0
    watopt = 0
    if form.has_key("DEBUMP"):
        debump = 1
    if form.has_key("HOPT"):
        hopt = 1
    if form.has_key("INPUT"):
        input = 1
    if form.has_key("HDEBUMP"):
        hdebump = 1
    if form.has_key("WATOPT"):
        watopt = 1 
    if form.has_key("PDBID"):
        file = getFile(form["PDBID"].value)
    elif form.has_key("PDB"):
        file = StringIO(form["PDB"].value)

    pdblist, errlist = readPDB(file)    
    if len(pdblist) == 0 and len(errlist) == 0:
        text = "Unable to find PDB file - Please make sure this is "
        text += "a valid PDB file ID!"
        print "Content-type: text/html\n"
        print text
        sys.exit(2)

    try:
        starttime = time.time()
        name = setID(starttime)
 
        pqrpath = startServer(name)
        header, lines = runPDB2PQR(pdblist, 0, ff, debump, hopt, hdebump, watopt)
        file = open(pqrpath, "w")
        file.write(header)
        for line in lines:
            file.write("%s\n" % string.strip(line))
        file.close()
                
        if input:
            import inputgen
            import psize
            igen = inputgen.inputgen()
            igen.method = "mg-auto"
            size = psize.Psize()
            igen.runinputgen(pqrpath, size)
                    
        endtime = time.time() - starttime
        createResults(header, input, name, endtime)
        logRun(form, endtime, len(pdblist))

    except StandardError, details:
        print "Content-type: text/html\n"
        print details
        createError(name, details)
    
if __name__ == "__main__":
    """ Determine if called from command line or CGI """
    
    if not os.environ.has_key("REQUEST_METHOD"):
        #import profile
        #profile.run("mainCommand()")
        mainCommand()    
    else:
        mainCGI()
