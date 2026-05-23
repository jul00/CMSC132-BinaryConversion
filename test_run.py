from run import Program

# NOP instruction: 32 zeros
nop = '0' * 32

# HALT instruction:
# opcode 10 -> binary 01010
# mode 0 -> 0000
# dest 0 -> 0000000
# operand 0 -> 0000000000000000
halt = '01010' + '0000' + '0000000' + '0' * 16

program = Program(start_address=10)
program.load_program([nop, halt], start_address=10)
program.reset(pc=10)
program.run()
program.dump_state()