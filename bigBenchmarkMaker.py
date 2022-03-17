#!/usr/bin/env python3
import os, sys, random

if len(sys.argv)<2:
    print("Error: No output file given.",file=sys.stderr)
    sys.exit(1)
    
outFileName = sys.argv[1]
random.seed(3)

NOF_PROPOSITIONS = 7
NOF_STATE_BITS = 11
NOF_BLOCKS = 6
MIN_NOF_ASSIGNMENTS_PER_BLOCK = 3
MAX_NOF_ASSIGNMENTS_PER_BLOCK = 7
MAX_NOF_VARS_USED_PER_BLOCK = 9
definedBits = set([])

with open(outFileName,"w") as outFile:

    # States
    allStateBits = ["s"+str(i) for i in range(NOF_STATE_BITS)]
    outFile.write("STATES "+" ".join(allStateBits)+"\n")
    outFile.write("INITIAL "+" ".join(["1" if random.random()>0.5 else "0" for i in range(NOF_STATE_BITS)])+"\n")
    definedBits.update(allStateBits)
    
    # Define Propositions
    propositionBits = ["p"+str(i) for i in range(NOF_PROPOSITIONS)]
    outFile.write("PROPOSITIONS "+" ".join(propositionBits)+"\n")
    definedBits.update(propositionBits)
    
    # Assign state bits to blocks
    howManyStatesPerBlock = [0 for i in range(NOF_BLOCKS)]
    nextStateDefsByBlock = [[] for i in range(NOF_BLOCKS)]
    for i in range(NOF_STATE_BITS):
        targetBlock = int(random.random()*NOF_BLOCKS)
        while howManyStatesPerBlock[targetBlock]+MAX_NOF_ASSIGNMENTS_PER_BLOCK>16:
            targetBlock = int(random.random()*NOF_BLOCKS)
        howManyStatesPerBlock[targetBlock] += 1    
                    
    postStatesSoFar = 0
    for i in range(NOF_BLOCKS):
        for j in range(howManyStatesPerBlock[i]):
            nextStateDefsByBlock[i].append("s"+str(postStatesSoFar))
            postStatesSoFar += 1
    del howManyStatesPerBlock
    del postStatesSoFar
    print("Assignment:",nextStateDefsByBlock)
    
    # Provide blocks blocks
    nofAdditionalVarsSoFar = 0    
    for block in range(NOF_BLOCKS):
        
        nofVarsToDefine = int(random.random()*(MAX_NOF_ASSIGNMENTS_PER_BLOCK-MIN_NOF_ASSIGNMENTS_PER_BLOCK)+MIN_NOF_ASSIGNMENTS_PER_BLOCK)
        
        # Function for defining the content of a new variable
        defVarList = list(definedBits)
        varsAlreadyUsedForBlock = []
        def nextAssignment(targetVar):
            outFile.write("LET "+targetVar+" ")
            def recurse(depth):
                p = random.random()
                if p<0.15 and depth<4:
                    return "| "+recurse(depth+1)+" "+recurse(depth+1)
                elif p<0.3 and depth<4:
                    return "& "+recurse(depth+1)+" "+recurse(depth+1)
                elif p<0.45 and depth<4:
                    return "^ "+recurse(depth+1)+" "+recurse(depth+1)
                elif p<0.6 and depth<4:
                    return "! "+recurse(depth+1)
                else:
                    if len(varsAlreadyUsedForBlock)>=MAX_NOF_VARS_USED_PER_BLOCK:
                        thisOne = random.choice(varsAlreadyUsedForBlock)
                    else:
                        thisOne = random.choice(defVarList)
                        if not thisOne in varsAlreadyUsedForBlock:
                            varsAlreadyUsedForBlock.append(thisOne)
                    return thisOne
                    
            outFile.write(recurse(1)+"\n")
        
        
        # Define aux. vars plus next state bits
        for i in range(0,nofVarsToDefine):
            nextVar = "v"+str(nofAdditionalVarsSoFar)
            nofAdditionalVarsSoFar += 1
            nextAssignment(nextVar)
            definedBits.add(nextVar)
        for a in nextStateDefsByBlock[block]:
            nextAssignment(a+"'")
        
        if block!=NOF_BLOCKS-1:
            outFile.write("NEWBLOCK\n")
            
    
