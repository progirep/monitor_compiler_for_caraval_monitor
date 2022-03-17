# Compiler for the binary format needed by the runtime monitor developed for the Caravel SoC

This repository contains a monitor compiler for a specialized monitoring microcontroller/System on chip component for runtime monitoring of reactive systems.

An explanation of what this compiler is good for, including an example of an input file for this monitor compiler can be found in the README of the repository of the monitoring component, which can be found [here](https://github.com/progirep/temporal_runtime_monitor_for_caravel).


## Usage

Running the compiler is simple: just call it on an input file, and the generated C code to be run on the Caravel SoC in order to program the monitor is emitted to the standard output.

For instance, the compiler can be run on the example input file as follows:

    ./compiler.py examples/simple.txt
    
## Fuzz test generator

To test the runtime monitoring component, there is also the script "randomtestmaper.py" in the repository, which, when providing a monitor description input file as parameter, produces some C code that can be run on the System on Chip in order to check if the monitoring component is working correctly. Example usage:

    ./randomtestmaker.py examples/simple.txt

    
## License

The monitor compiler is available under a GPLv3 license. 
