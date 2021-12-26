#!/usr/bin/env python3
import os, sys, random

if len(sys.argv)<2:
    print("Error: Need input file name.",file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1],"r") as inFile:
    allInputLines = [a.strip().split(" ") for a in inFile.readlines()]
    
stateBits = None # List of state bits (ordered)
initialBits = None # Initial valies (0 and 1 strings) for the state bits
propositions = None # List of propositions (ordered)
blockBitsNeeded = [set([])] # All propositions that are input to the respective block
blockLetStatements = [[]] # The LET statements in the block, ordered
definedVars = {} # Which vars are defined in which block so far - used during reading the input to find usage of undefined var's


# Iterate through all input lines
for lineNo,line in enumerate(allInputLines):
    if len(line)>0 and line[0]!="":
        if line[0]=="STATES":
            assert stateBits is None
            stateBits = line[1:]
            assert not " " in stateBits
            definedVars.update({a : -1 for a in stateBits})
        elif line[0]=="INITIAL":
            assert initialBits is None
            initialBits = line[1:]
            assert not " " in initialBits
        elif line[0]=="PROPOSITIONS":
            assert propositions is None
            propositions = line[1:]
            assert not " " in propositions
            definedVars.update({a : -1 for a in propositions})
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
                    if definedVars[x]<len(blockLetStatements)-1:
                        blockBitsNeeded[-1].add(x)
                    definedVars[line[1]] = len(blockLetStatements)-1
            
            
           
        elif line[0]=="NEWBLOCK":
            blockBitsNeeded.append(set([]))
            blockLetStatements.append([])
        else:
            raise Exception("Error: line command "+str(line[0])+" unknown.")   

# Check if all next states are defined
for a in stateBits:
    if not a+"'" in definedVars:
        raise Exception("Error: No next state bit for "+str(a)+" defined.")
        


currentState = {}
for i,a in enumerate(initialBits):
    if a=="1":
        currentState[stateBits[i]] = True
    elif a=="0":
        currentState[stateBits[i]] = False
    else:
        raise Exception("Illegal initial state component part: "+a)

# Generate test
for step in range(0,10):

    # Enrich current state by atomic propositions
    nextPropositionValues = int(random.random()*(1 << len(propositions)))
        
    for i,p in enumerate(propositions):
        if (nextPropositionValues & (1 << i))>0:
            currentState[p] = True
        else:
            currentState[p] = False
    print("monitorStep("+hex(nextPropositionValues)+");")            
                
    # Compute successor state values
    for block in range(len(blockLetStatements)):
    
        # Compute lookup tables
        for a in blockLetStatements[block]:
            def recurseParse(pos):
                if a[pos]=="|":
                    res1,posB = recurseParse(pos+1)
                    res2,posC = recurseParse(posB)
                    return res1 or res2,posC
                elif a[pos]=="&":
                    res1,posB = recurseParse(pos+1)
                    res2,posC = recurseParse(posB)
                    return res1 and res2,posC
                elif a[pos]=="^":
                    res1,posB = recurseParse(pos+1)
                    res2,posC = recurseParse(posB)
                    return res1 ^ res2,posC
                elif a[pos]=="!":
                    res1,posB = recurseParse(pos+1)
                    return not res, posB
                else:
                    return currentState[a[pos]], pos+1                
            result,pos = recurseParse(1)
            if pos!=len(a):
                raise Exception("Stray characters in line: LET "," ".join(a)," end at ",pos)
            currentState[a[0]] = result
  

    # Compute next state values
    for s in stateBits:
        currentState[s] = currentState[s+"'"]

    # Compute state afterwards
    nextState = 0
    for i,p in enumerate(stateBits):
        if currentState[p]:
            nextState = nextState | (1 << i)
    
    # print("// Values of all bits after APs: "+str(currentState))
            
    # Check only the first 60 state bits -- the other ones may be "tainted" by values from the final spurious table lookup 
                
    print("if (*((volatile uint32_t*)(0x30020008))!="+hex(nextState & ((1 << 32)-1))+") failTest();")
    print("if (((*((volatile uint32_t*)(0x3002000C))) & "+hex((1<<28)-1)+")!="+hex((nextState >> 32) & ((1<<28)-1))+") failTest();")
    
