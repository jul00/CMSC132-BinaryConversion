from run import Program
from compiler import Instruction
from bin_convert import HalfPrecision, Length
from storage import memory, register, variable


def reset_state():
    for i in range(128):
        memory.store(i, 0)
    for i in range(32):
        register.store(i, 0)


def resolve_address(token):
    token = token.upper()
    if token.startswith('R') and token[1:].isdigit():
        return int(variable.load(token))
    if token in variable.data:
        return int(variable.load(token))
    if token.isdigit():
        return int(token)
    raise ValueError(f'Unknown token: {token}')


def build_instruction(op, op1_mode, op1_addr, op2_mode='000', op2_addr=0, immediate=None):
    opcode = Instruction.encodeOpcode(op)
    op1_bits = op1_mode + Length.addZeros(op1_addr, Length.opAddr)

    if immediate is not None:
        try:
            value = int(immediate)
        except ValueError:
            value = float(immediate)
        hp = HalfPrecision.hpdec2bin(value)
        ib = hp[0]
        rb = '1'
        op2_bits = hp[1:11]
        extra_bits = hp[11:]
    else:
        ib = '0'
        rb = '0'
        op2_bits = op2_mode + Length.addZeros(op2_addr, Length.opAddr)
        extra_bits = '0' * 5

    return opcode + ib + op1_bits + rb + op2_bits + extra_bits


def run_raw_program(instructions, start_address=10):
    program = Program(start_address=start_address)
    program.reset(pc=start_address)
    program.load_program(instructions, start_address=start_address)
    program.run()
    return program


def assert_equal(actual, expected, message=''):
    if actual != expected:
        raise AssertionError(f'{message} Expected {expected}, got {actual}')


def test_alu_and_prnt():
    print('Running ALU + PRNT tests...')
    reset_state()
    program_lines = [
        'MOV R1 5',
        'ADD R1 3',
        'SUB R1 1',
        'MUL R1 2',
        'DIV R1 4',
        'PRNT R1',
        'EOP'
    ]
    program = Program(program_lines, start_address=10)
    program.run()
    assert_equal(program.get_register('R1'), 3.5, 'ALU chain result mismatch.')


def test_jumps():
    print('Running jump tests...')
    reset_state()
    program_lines = [
        'MOV R1 33',
        'MOV JR 1',
        'MOV R4 15',
        'JGT R4',
        'MOV R1 0',
        'EOP'
    ]
    program = Program(program_lines, start_address=10)
    program.run()
    assert_equal(program.get_register('R1'), 33, 'JGT failed to skip instruction.')

    reset_state()
    program_lines = [
        'MOV R1 44',
        'MOV JR 0',
        'MOV R4 15',
        'JEQ R4',
        'MOV R1 0',
        'EOP'
    ]
    program = Program(program_lines, start_address=10)
    program.run()
    assert_equal(program.get_register('R1'), 44, 'JEQ failed to skip instruction.')


def test_memory_addressing_modes():
    print('Running memory addressing tests...')

    reset_state()
    memory.store(20, 42)
    program = run_raw_program([
        build_instruction('MOV', '000', resolve_address('R1'), '010', 20),
        Instruction.encode('EOP')
    ])
    assert_equal(program.get_register('R1'), 42, 'Direct memory load failed.')

    reset_state()
    memory.store(30, 20)
    memory.store(20, 15)
    program = run_raw_program([
        build_instruction('MOV', '000', resolve_address('R1'), '011', 30),
        Instruction.encode('EOP')
    ])
    assert_equal(program.get_register('R1'), 15, 'Indirect memory load failed.')

    reset_state()
    register.store(resolve_address('R2'), 30)
    memory.store(30, 99)
    program = run_raw_program([
        build_instruction('MOV', '000', resolve_address('R1'), '001', resolve_address('R2')),
        Instruction.encode('EOP')
    ])
    assert_equal(program.get_register('R1'), 99, 'Register indirect load failed.')

    reset_state()
    register.store(resolve_address('R2'), 40)
    memory.store(40, 123)
    program = run_raw_program([
        build_instruction('MOV', '000', resolve_address('R1'), '110', resolve_address('R2')),
        Instruction.encode('EOP')
    ])
    assert_equal(program.get_register('R1'), 123, 'Autoinc load failed.')
    assert_equal(register.load(resolve_address('R2')), 41, 'Autoinc register not incremented.')

    reset_state()
    register.store(resolve_address('R2'), 41)
    memory.store(40, 77)
    program = run_raw_program([
        build_instruction('MOV', '000', resolve_address('R1'), '111', resolve_address('R2')),
        Instruction.encode('EOP')
    ])
    assert_equal(program.get_register('R1'), 77, 'Autodec load failed.')
    assert_equal(register.load(resolve_address('R2')), 40, 'Autodec register not decremented.')

    reset_state()
    register.store(resolve_address('R1'), 55)
    program = run_raw_program([
        build_instruction('MOV', '010', 20, '000', resolve_address('R1')),
        Instruction.encode('EOP')
    ])
    assert_equal(memory.load(20), 55, 'Direct memory store failed.')


def test_opcode_encoding():
    print('Running opcode encoding coverage...')
    Instruction.encode('MOV R1 1')
    Instruction.encode('ADD R1 1')
    Instruction.encode('SUB R1 1')
    Instruction.encode('MUL R1 1')
    Instruction.encode('DIV R1 1')
    Instruction.encode('JEQ R1')
    Instruction.encode('JNE R1')
    Instruction.encode('JLT R1')
    Instruction.encode('JLE R1')
    Instruction.encode('JGT R1')
    Instruction.encode('JGE R1')
    Instruction.encode('JMP R1')
    Instruction.encode('CALL R1 1')
    Instruction.encode('RET R1 1')
    Instruction.encode('SCAN R1 1')
    Instruction.encode('PRNT R1')
    Instruction.encode('FUNC')
    Instruction.encode('EOP')


def main():
    test_alu_and_prnt()
    test_jumps()
    test_memory_addressing_modes()
    test_opcode_encoding()
    print('All tests passed.')


if __name__ == '__main__':
    main()