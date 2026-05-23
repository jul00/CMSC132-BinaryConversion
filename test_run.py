from run import Program

program_lines = [
    'MOV R1 5',
    'ADD R1 3',
    'EOP'
]

program = Program(program_lines)
program.run()
program.dump_state()
print('R1 =', program.get_register('R1'))