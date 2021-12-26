#!/usr/bin/env python3
import os, sys

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
        
# Compute transitive bits needed relation
bitsNeeded = [set() for i in range(len(blockLetStatements))] # Which bits still need to be present at the beginning of the block? -- one longer than the number of blocks to store which bits should be present *after* the last block
bitsNeeded.append(set([a + "'" for a in stateBits]))
for blockNo in range(len(blockLetStatements)-1,-1,-1):
    # Compute: Everything that is needed in the block afterwards plus what is used here minus what is defined here 
    nextSet = set(bitsNeeded[blockNo+1])
    nextSet.update(blockBitsNeeded[blockNo])
    for a in blockLetStatements[blockNo]:
        if a[0] in nextSet:
            nextSet.remove(a[0])
    bitsNeeded[blockNo] = nextSet
    
print("==============Bits needed before every block=================")
for i in range(len(blockLetStatements)):
    print(" - Block "+str(i)+": "+" ".join(bitsNeeded[i]))
print(" - Terminal bits: "+" ".join(bitsNeeded[-1]))


# Compute which bits are computed by each block and how many bits are present at the end of each monitor cycle
bitsComputedByBlocks = [] # Which bits are computed by which block?
for i in range(len(blockLetStatements)):
    bitsComputedByBlocks.append([])
    for a in blockLetStatements[i]:
        if a[0] in bitsNeeded[i+1]:
            bitsComputedByBlocks[-1].append(a[0])
            
print("==============Bits computed by blocks =================")
for i in range(len(blockLetStatements)):
    print(" - Block "+str(i)+": "+" ".join(bitsComputedByBlocks[i]))
    
    
print("==============Number of Bits for input ================")
bitDefinitionsBeforeLookupBlocks = [{}] # Stores mapping from variable names to monitor state bit numbers at the beginning of blocks
nofReservedBitsInput = len(propositions)
while (nofReservedBitsInput & 3)>0:
    nofReservedBitsInput += 1
if len(stateBits)+nofReservedBitsInput>64:
    raise Exception("Error: State bits plus propositions exceed 64 bits -- too much for the monitor.")
if len(stateBits)>60: # Can only fire if number of input bits is 0. Very special special case.
    raise Exception("Error: State bits exceed 60 bits -- unable to sort the final bits in the end without a nibble of free space.")

for i,p in enumerate(stateBits):
    bitDefinitionsBeforeLookupBlocks[0][p] = i
    
for i,p in enumerate(propositions):
    bitDefinitionsBeforeLookupBlocks[0][p] = 60+(i%4)-4*(i//4)

print("Number of bits reserved for the input:",nofReservedBitsInput)
print("Initial block bit assignment: ",bitDefinitionsBeforeLookupBlocks[0])

# Do the block encoding
print("===============Computing lookup-blocks=================")
lookupBlocks = [] # Lookup tables for the blocks
lookupBlockOutputSizes = [] # Sizes of the output of the blocks
lookupBlockInputSizes = [] # Sizes of the local gathered input of the blocks
lookupBlockMaskGather = [] # Masks for gathering the bits for the lookup (one per block)
lookupBlockMaskFilter = [] # Masks for filtering the bits at the end of the block (one per block) 

for block in range(len(blockLetStatements)):
    print("Block "+str(block)+" local inputs needed: ",blockBitsNeeded[block])
    
    # Compute input masks and local input bit positions
    inputMask = 0
    inputLocal = {} # Used temporarily
    for bit in blockBitsNeeded[block]:
        position = bitDefinitionsBeforeLookupBlocks[block][bit]
        inputMask = inputMask + (1 << position)
        inputLocal[position] = bit
    localInputPos = {} # Where are the bits in the address for the lookup table?
    for bitpos in range(64):
        if bitpos in inputLocal:
            nextPos = len(localInputPos)
            localInputPos[nextPos] = inputLocal[bitpos]
    del inputLocal
    lookupBlockMaskGather.append(inputMask)
    print("Mask:",hex(inputMask))
    print("Local input bits: ",localInputPos)
    lookupBlockInputSizes.append(len(localInputPos))
    if len(localInputPos)==0:
        raise Exception("Error: This compiler current does not support blocks that need no input. Use a dummy input if needed") # Makes sure that all look-up tables are of size multiple of 2, which means that bytes will not be shared between lookup tables

    # Compute next bit positions - part 1: Filtering
    outputMask = 0
    neededAfterwards = {}
    for proposition in bitDefinitionsBeforeLookupBlocks[block]:
        if proposition in bitsNeeded[block+1]:
            neededAfterwards[bitDefinitionsBeforeLookupBlocks[block][proposition]] = proposition
            outputMask = outputMask + (1 << bitDefinitionsBeforeLookupBlocks[block][proposition])
    lookupBlockMaskFilter.append(outputMask)
    bitDefinitionsBeforeLookupBlocks.append({})
    for bitpos in range(64):
        if bitpos in neededAfterwards:
            nofSizeSoFar = len(bitDefinitionsBeforeLookupBlocks[-1])
            bitDefinitionsBeforeLookupBlocks[-1][neededAfterwards[bitpos]] = nofSizeSoFar
    
    # Compute pre-filter bit order
    nofOutputBitsRounded = len(bitsComputedByBlocks[block])
    if nofOutputBitsRounded>16:
        raise Exception("Defined output block with too many exported output bits: ",bitsComputedByBlocks[block])
    while (nofOutputBitsRounded!=4) and (nofOutputBitsRounded!=8) and (nofOutputBitsRounded!=16):
        nofOutputBitsRounded += 1
    lookupBlockOutputSizes.append(nofOutputBitsRounded)

    # Size check
    if len(bitDefinitionsBeforeLookupBlocks[-1])+nofOutputBitsRounded>64:
        raise Exception("Error: State vector capacity exceeded.")

    for i,a in enumerate(bitsComputedByBlocks[block]):
        bitDefinitionsBeforeLookupBlocks[-1][a] = 64-nofOutputBitsRounded+i
    print("Bit positions afterwards: ", bitDefinitionsBeforeLookupBlocks[-1])
    
    
    # Compute lookup tables
    lookupTable = []
    for bitAssignment in range(1 << len(localInputPos)):
        thisAssignment = {}
        for (a,b) in localInputPos.items():
            if (bitAssignment & (1 << a)) > 0:
                thisAssignment[b] = True
            else:
                thisAssignment[b] = False
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
                    return thisAssignment[a[pos]], pos+1                
            result,pos = recurseParse(1)
            if pos!=len(a):
                raise Exception("Stray characters in line: LET "," ".join(a)," end at ",pos)
            thisAssignment[a[0]] = result
        # Gather outputs
        outVal = 0
        for i,a in enumerate(bitsComputedByBlocks[block]):
            if thisAssignment[a]:
                outVal += (1 << i)
        lookupTable.append(outVal)
    lookupBlocks.append(lookupTable)
    print("Lookup table:",lookupTable)


# ==========================================================================
# Compile the lookup tables into data chunk for address 0x30020000 and later
# ==========================================================================
bytesLookupTables = []
startingPositionsLookupTables = [None for i in range(0,len(blockLetStatements))]
for lutSize in [16,8,4]:
    for blockNum in range(len(blockLetStatements)):
        if (lookupBlockOutputSizes[blockNum] == lutSize):
            startingPositionsLookupTables[blockNum] = len(bytesLookupTables)
            if lutSize==16:
                for a in lookupBlocks[blockNum]:
                    bytesLookupTables.append(a % 256)
                    bytesLookupTables.append(a // 256)
            elif lutSize==8:
                for a in lookupBlocks[blockNum]:
                    bytesLookupTables.append(a)
            elif lutSize==4:
                for i in range(0,len(lookupBlocks[blockNum]),2):
                    bytesLookupTables.append(lookupBlocks[blockNum][i]+16*lookupBlocks[blockNum][i+1])
if len(bytesLookupTables)>8192:
    raise Exception("Error: Not enough space in the lookup table space of 8 kB")
while (len(bytesLookupTables)%4)!=0:
    bytesLookupTables.append(0)
            
    
# Prepare the mask for the final block
lastMask = 0
lastPos = -1
for a in stateBits:
    nextPos = bitDefinitionsBeforeLookupBlocks[-1][a+"'"]
    if nextPos<lastPos:
        raise Exception("Error: Order to state bits is not right at the end.")
    else:
        lastMask += (1 << nextPos)
        lastPos = nextPos    
print("Final mask: ",hex(lastMask))


# ==========================================================
# Write code
# ==========================================================
print("=====================Generated code===================")
print("const uint32_t monitoringLookupTables[] = {",end="")
bytesLookupTables = [hex(a)[2:] for a in bytesLookupTables]
bytesLookupTables = [(2-len(a))*"0"+a for a in bytesLookupTables]
for i in range(0,len(bytesLookupTables),4):
    print("0x"+bytesLookupTables[i+3]+bytesLookupTables[i+2]+bytesLookupTables[i+1]+bytesLookupTables[i+0],end="")
    if i!=len(bytesLookupTables)-4:
        print(",",end="")
    if (i%4==3):
        print("\n\t",end="")
print("};")
print("const uint32_t monitoringMaskTable[] = {",end="")
for i in range(len(blockLetStatements)):
    print(hex(lookupBlockMaskGather[i] & ((1<<32)-1)),end=",")
    print(hex(lookupBlockMaskGather[i] >> 32),end=",")
    print(hex(lookupBlockMaskFilter[i] & ((1<<32)-1)),end=",")
    print(hex(lookupBlockMaskFilter[i] >> 32),end="")
    print(",\n\t",end="")
# Final mask
print("0,0,"+hex(lastMask & ((1<<32)-1))+","+hex(lastMask>>32)+"};")
# Control information at the end of SRAM1
controlInformationAtEnd = []
for i in range(len(blockLetStatements)):
    # Compute control information
    addressInfo = startingPositionsLookupTables[i]
    if lookupBlockOutputSizes[i]==4:
        lenInfo = 2
        addressInfo = addressInfo * 2
    elif lookupBlockOutputSizes[i]==8:
        lenInfo = 1
    elif lookupBlockOutputSizes[i]==16:
        lenInfo = 0
        addressInfo = addressInfo // 2
    else:
        raise Exception("Internal error.")
    controlInformationAtEnd.append((lenInfo << 14) + addressInfo)
    assert addressInfo < 1<<14
    
# Add final control information for the update block
controlInformationAtEnd.append((1<<15)+(1<<14))
if (len(controlInformationAtEnd) & 1)>0:
    controlInformationAtEnd.append(0)

# Print
controlInformationAtEnd = [hex(a)[2:] for a in controlInformationAtEnd]
controlInformationAtEnd = [(4-len(a))*"0"+a for a in controlInformationAtEnd]
print("const uint32_t monitoringControlInfo[] = {",end="")    
for i in range(0,len(controlInformationAtEnd),2):
    print("0x"+controlInformationAtEnd[i+1]+controlInformationAtEnd[i],end="")
    if i+2!=len(controlInformationAtEnd):
        print(",",end="")
    if (i % 8)==6:
        print("\n\t")
print("};")

# Doesn't fit?
if len(controlInformationAtEnd)*2+len(lookupBlockMaskGather)*16>1024:
    raise Exception("Error: Number of blocks in monitor is too large -- the data for the control information SRAM is too large.")

# resetMonitor Code
print("void resetMonitor() {")
initialEncoded = 0
for i,a in enumerate(initialBits):
    if a=="1":
        initialEncoded += (1 << i)
    elif a=="0":
        pass
    else:
        raise Exception("Illegal initial state component part: "+a)

print("\t*((volatile uint32_t*)(0x30020008)) = "+hex(initialEncoded & ((1<<32)-1))+";")
print("\t*((volatile uint32_t*)(0x3002000C)) = "+hex(initialEncoded >> 32)+";")
print("}\n")


# initMonitorCode
print("void initMonitor() {")
print("\t// Fill lookup table memory")
print("\tfor (unsigned int i=0;i<"+str(len(bytesLookupTables))+";i+=4) {")
print("\t\t*((volatile uint32_t*)(0x30010000+i)) = monitoringLookupTables[i>>2];")
print("\t}")
print("\t// Fill mask table")
print("\tfor (unsigned int i=0;i<"+str(4*(len(blockLetStatements)+1))+";i++) {")
print("\t\t*((volatile uint32_t*)(0x30000000+4*i)) = monitoringMaskTable[i];")
print("\t}")
print("\t// Fill control information part")
print("\tfor (unsigned int i=0;i<"+str(len(controlInformationAtEnd)//2)+";i++) {")
print("\t\t*((volatile uint32_t*)(0x30000000+1024-4-4*i)) = monitoringControlInfo[i];")
print("\t}")
print("\t// Set control register")
print("\t*((volatile uint32_t*)(0x30020000)) = "+str(len(blockLetStatements))+" /*Nof last block*/ + (0 << 6) /*current block*/;") 
print("\t// Trigger cycle to fill buffers")
print("\t*((volatile uint32_t*)(0x30020004)) = 0;")
print("\tresetMonitor();")
print("}\n")


print("void monitorStep(uint32_t data) {")
print("\t*((volatile uint32_t*)(0x30020004)) = data;")
print("}\n")
