import copy
import cocotb
from cocotb.triggers import Timer


# Make sure to set FILE_NAME
# to the filepath of the .log
# file you are working with
CHAIN_LENGTH = 13
FILE_NAME    = "./adder/adder.log"



# Holds information about a register
# in your design.

################
# DO NOT EDIT!!!
################
class Register:

    def __init__(self, name) -> None:
        self.name = name            # Name of register, as in .log file
        self.size = -1              # Number of bits in register

        self.bit_list = list()      # Set this to the register's contents, if you want to
        self.index_list = list()    # List of bit mappings into chain. See handout

        self.first = -1             # LSB mapping into scan chain
        self.last  = -1             # MSB mapping into scan chain


# Holds information about the scan chain
# in your design.
        
################
# DO NOT EDIT!!!
################
class ScanChain:

    def __init__(self) -> None:
        self.registers = dict()     # Dictionary of Register objects, indexed by 
                                    # register name
        
        self.chain_length = 0       # Number of FFs in chain


# Sets up a new ScanChain object
# and returns it

################     
# DO NOT EDIT!!!
################
def setup_chain(filename):

    scan_chain = ScanChain()

    f = open(filename, "r")
    for line in f:
        linelist = line.split()
        index, name, bit = linelist[0], linelist[1], linelist[2]

        if name not in scan_chain.registers:
            reg = Register(name)
            reg.index_list.append((int(bit), int(index)))
            scan_chain.registers[name] = reg

        else:
            scan_chain.registers[name].index_list.append((int(bit), int(index)))
        
    f.close()

    for name in scan_chain.registers:
        cur_reg = scan_chain.registers[name]
        cur_reg.index_list.sort()
        new_list = list()
        for tuple in cur_reg.index_list:
            new_list.append(tuple[1])
        
        cur_reg.index_list = new_list
        cur_reg.bit_list   = [0] * len(new_list)
        cur_reg.size = len(new_list)
        cur_reg.first = new_list[0]
        cur_reg.last  = new_list[-1]
        scan_chain.chain_length += len(cur_reg.index_list)

    return scan_chain


# Prints info of given Register object

################
# DO NOT EDIT!!!
################
def print_register(reg):
    print("------------------")
    print(f"NAME:    {reg.name}")
    print(f"BITS:    {reg.bit_list}")
    print(f"INDICES: {reg.index_list}")
    print("------------------")


# Prints info of given ScanChain object

################   
# DO NOT EDIT!!!
################
def print_chain(chain):
    print("---CHAIN DISPLAY---\n")
    print(f"CHAIN SIZE: {chain.chain_length}\n")
    print("REGISTERS: \n")
    for name in chain.registers:
        cur_reg = chain.registers[name]
        print_register(cur_reg)



#-------------------------------------------------------------------

# This function steps the clock once.
    
# Hint: Use the Timer() builtin function
async def step_clock(dut):

    # Set clock high
    dut.clk <= 1
    await Timer(10, units="ns")
    # Set clock low
    dut.clk <= 0
    await Timer(10, units="ns")

    pass
    

#-------------------------------------------------------------------

# This function places a bit value inside FF of specified index.
        
# Hint: How many clocks would it take for value to reach
#       the specified FF?
        
async def input_chain_single(dut, bit, ff_index):

    # Enable scan mode
    dut.scan_en <= 1
    # The bit must be clocked in ff_index+1 times to propagate
    # from scan_in to the desired flip-flop in the chain.
    for _ in range(ff_index + 1):
        dut.scan_in <= bit
        await step_clock(dut)

    pass
    
#-------------------------------------------------------------------

# This function places multiple bit values inside FFs of specified indexes.
# This is an upgrade of input_chain_single() and should be accomplished
#   for Part H of Task 1
        
# Hint: How many clocks would it take for value to reach
#       the specified FF?
        
async def input_chain(dut, bit_list, ff_index):

    # Activate scan mode.
    dut.scan_en <= 1

    # We plan a total of (ff_index + len(bit_list)) clock cycles.
    # In a shift register, a value inserted at cycle c will appear at position:
    #   position = (total_cycles - c)
    # To place bit_list[0] at flip-flop ff_index, we need:
    #   total_cycles - c₀ = ff_index   →   c₀ = total_cycles - ff_index = len(bit_list)
    # Similarly, bit_list[1] must be shifted in one clock earlier (so it travels one more stage),
    # and so on. This means we must clock in the bits in reverse order.
    
    total_cycles = ff_index + len(bit_list)
    
    # Clock in the bits from the list in reverse order.
    for i in range(len(bit_list)):
        # i = 0 clocks in bit_list[-1], i = len(bit_list)-1 clocks in bit_list[0].
        dut.scan_in <= bit_list[len(bit_list) - 1 - i]
        await step_clock(dut)
        
    # After inserting all list bits, add ff_index dummy cycles (e.g. zeros)
    # so that each bit has the proper number of clocks to propagate.
    for _ in range(ff_index):
        dut.scan_in <= 0
        await step_clock(dut)

    pass

#-----------------------------------------------

# This function retrieves a single bit value from the
# chain at specified index 
        
async def output_chain_single(dut, ff_index):

    # Enable scan mode
    dut.scan_en <= 1
    # Calculate the number of clock cycles needed for the desired bit to propagate
    # from its flip-flop to the scan_out (last FF). For a chain of CHAIN_LENGTH,
    # the bit at index ff_index will appear at scan_out after (CHAIN_LENGTH - ff_index - 1) clocks.
    shift_cycles = CHAIN_LENGTH - ff_index - 1
    for _ in range(shift_cycles):
        await step_clock(dut)
    # Return the bit now present at scan_out
    return int(dut.scan_out.value)
    

#-----------------------------------------------

# This function retrieves a single bit value from the
# chain at specified index 
# This is an upgrade of input_chain_single() and should be accomplished
#   for Part H of Task 1
        
async def output_chain(dut, ff_index, output_length):

    # Enable scan mode.
    dut.scan_en <= 1
    # Shift until the bit from flip-flop at ff_index reaches scan_out.
    # In a chain of CHAIN_LENGTH flip-flops, the bit in ff_index appears after:
    #   CHAIN_LENGTH - ff_index - 1 clocks.
    shift_cycles = CHAIN_LENGTH - ff_index - 1
    for _ in range(shift_cycles):
        await step_clock(dut)
    
    # Collect the desired output bits.
    result = []
    for i in range(output_length):
        # Read the current scan_out value.
        result.append(int(dut.scan_out.value))
        # Shift once more to bring the next bit into scan_out,
        # except after reading the last bit.
        if i < output_length - 1:
            await step_clock(dut)
    
    return result

#-----------------------------------------------

# Your main testbench function

@cocotb.test()
async def test(dut):

    global CHAIN_LENGTH
    global FILE_NAME        # Make sure to edit this guy
                            # at the top of the file

    # Setup the scan chain object
    chain = setup_chain(FILE_NAME)

    # Choose test values:
    # a_reg and b_reg are 4-bit values and x_out is 5 bits.
    a_val = 2      # For example, 2 in decimal (binary 0010 LSB-first: [0,1,0,0])
    b_val = 3      # For example, 3 in decimal (binary 0011 LSB-first: [1,1,0,0])
    expected = a_val + b_val  # Expected sum: 5 (binary 00101 LSB-first: [1,0,1,0,0])

    # Create bit lists (all LSB-first) for each register.
    # According to the chain mapping:
    #   indices 0-4  --> x_out (unused, so set to 0)
    #   indices 5-8  --> a_reg (4 bits)
    #   indices 9-12 --> b_reg (4 bits)
    x_out_bits = [0] * 5
    a_bits = num_to_bit_list(a_val, 4)
    b_bits = num_to_bit_list(b_val, 4)

    # Combine into one full-chain bit list.
    full_chain = x_out_bits + a_bits + b_bits
    # full_chain length should equal CHAIN_LENGTH

    # Feed the inputs into the chain in one pass (starting at index 0).
    await input_chain(dut, full_chain, 0)

    # Disable scan mode so that the adder computes the sum.
    dut.scan_en <= 0
    # Step the clock one cycle to perform the addition.
    await step_clock(dut)

    # Read the 5-bit result from x_out (starting at chain index 0).
    out_bits = await output_chain(dut, 0, 5)

    # Convert the output bit list (LSB-first) into an integer.
    result = 0
    for i, bit in enumerate(out_bits):
        result |= (bit << i)

    # Optional: display chain registers before/after the clock cycle.
    print_chain(chain)

    if result != expected:
        raise cocotb.result.TestFailure(f"Adder result incorrect: got {result}, expected {expected}")
    else:
        dut._log.info(f"Adder test passed: {a_val} + {b_val} = {result}")

def num_to_bit_list(num, width):
    # Return a list of bits (LSB first) representing num in fixed width.
    return [(num >> i) & 1 for i in range(width)]
