#!/usr/bin/env python3
import os, sys

if len(sys.argv)<2:
    print("Error: Need input file name.",file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1],"r") as inFile:
    allInputLines = [a.strip().split(" ") for a in inFile.readlines()]
    
stateBits = None
initialBits = None
propositions = None
blockBitsNeeded = [set([])]
blockLetStatements = [[]]
definedVars = set([])


# Iterate through all input lines
for lineNo,line in enumerate(allInputLines):
    if len(line)>0:
        if line[0]=="STATES":
            assert stateBits is None
            stateBits = line[1:]
            assert not " " in stateBits
            definedVars.update(stateBits)
        elif line[0]=="INITIAL":
            assert initialBits is None
            initialBits = line[1:]
            assert not " " in initialBits
        elif line[0]=="PROPOSITIONS":
            assert propositions is None
            propositions = line[1:]
            assert not " " in propositions
            definedVars.update(propositions)
        elif line[0]=="LET":
            blockLetStatements[-1].append(line[1:])
            if line[1] in definedVars:
                raise Exception("Error in input line "+str(lineNo+1)+": Variable "+line[1]+" was defined earlier.")
            for x in line[2:]:
                if x in ["&","|","!","^"]:
                    pass
                elif not x in definedVars:
                    raise Exception("Error in input line "+str(lineNo+1)+": Unknown variable "+x+" - defined are: "+str(definedVars))
                else:
                    blockBitsNeeded[-1].add(x)
                    definedVars.add(line[1])
            
            
            # Check that the next state bits are given in the right order.
            if line[1].endswith("'"):
                posStateBit = stateBits.index(line[1][0:-1])
                if posStateBit>0:
                    if not stateBits[posStateBit-1]+"'" in definedVars:
                        raise Exception("Next state bits not defined in the right order: "+line[1]+" is not preceded by "+stateBits[posStateBit-1]+"'")
            
        elif line[0]=="NEWBLOCK":
            blockBitsNeeded.append(set([]))
            blockLetStatements.append([])
            

# Check if all next states are defined
for a in stateBits:
    if not a+"'" in definedVars:
        raise Exception("Error: No next state bit for "+str(a)+" defined.")
        
# Compute transitive bits needed relation
bitsNeeded = [set() for i in range(len(blockLetStatements))]
bitsNeeded.append(set([a + "'" for a in stateBits]))
for blockNo in range(len(blockLetStatements)-1,-1,-1):
    # Compute: Everything that is needed in the block afterwards minus what is defined here plus what is used here
    nextSet = set(bitsNeeded[blockNo+1])
    for a in blockLetStatements[blockNo]:
        if a[0] in nextSet:
            nextSet.remove(a[0])
    nextSet.update(blockBitsNeeded[blockNo])
    bitsNeeded[blockNo] = nextSet
    
print("==============Bits needed before every block=================")
for i in range(len(blockLetStatements)):
    print(" - Block "+str(i)+": "+" ".join(bitsNeeded[i]))
print(" - Terminal bits: "+" ".join(bitsNeeded[-1]))


# Compute which values are computed by each block and how many 
