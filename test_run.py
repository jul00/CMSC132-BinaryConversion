from run import Program
from compiler import Instruction
from bin_convert import HalfPrecision, Length
from storage import memory, register, variable


def reset_state():
    for i in range(128):
        memory.store(i, 0)
    for i in range(32):
        register.store(i, 0)
    variable.data["MSG"] = {}
    variable.data["MI"] = 0
    register.store(variable.load("BR"), 9)
    register.store(variable.load("XR"), 77)
    register.store(variable.load("ACC"), 0)
    register.store(variable.load("IR"), 9)
    register.store(variable.load("PC"), 10)
    register.store(variable.load("JR"), 0)
    register.store(variable.load("CR"), 0)


def assert_equal(actual, expected, message=''):
    if actual != expected:
        raise AssertionError(f'{message} Expected {expected}, got {actual}')


def get_register(name):
    addr = int(variable.load(name))
    return register.load(addr)


def test_alu_and_prnt():
    print('Running ALU + PRNT tests...')
    reset_state()
    Program([
        'MOV R1 5',
        'ADD R1 3',
        'SUB R1 1',
        'MUL R1 2',
        'DIV R1 4',
        'PRNT R1',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 3.5, 'ALU chain result mismatch.')


def test_jumps():
    print('Running jump tests...')
    reset_state()
    Program([
        'MOV R1 33',
        'MOV JR 1',
        'MOV R4 15',
        'JGT R4',
        'MOV R1 0',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 33, 'JGT failed to skip instruction.')

    reset_state()
    Program([
        'MOV R1 44',
        'MOV JR 0',
        'MOV R4 15',
        'JEQ R4',
        'MOV R1 0',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 44, 'JEQ failed to skip instruction.')


def test_memory_addressing_modes():
    print('Running memory addressing tests...')

    reset_state()
    memory.store(3, 42)
    Program(['MOV R1 C', 'EOP'])
    Program.run()
    assert_equal(get_register('R1'), 42, 'Direct memory load failed.')

    reset_state()
    memory.store(3, 20)
    memory.store(20, 15)
    Program(['MOV R1 (C)', 'EOP'])
    Program.run()
    assert_equal(get_register('R1'), 15, 'Indirect memory load failed.')

    reset_state()
    register.store(2, 30)
    memory.store(30, 99)
    Program(['MOV R1 (R2)', 'EOP'])
    Program.run()
    assert_equal(get_register('R1'), 99, 'Register indirect load failed.')

    reset_state()
    register.store(2, 40)
    memory.store(40, 123)
    Program(['MOV R1 (R2)+', 'EOP'])
    Program.run()
    assert_equal(get_register('R1'), 123, 'Autoinc load failed.')
    assert_equal(register.load(2), 41, 'Autoinc register not incremented.')

    reset_state()
    register.store(2, 41)
    memory.store(40, 77)
    Program(['MOV R1 -(R2)', 'EOP'])
    Program.run()
    assert_equal(get_register('R1'), 77, 'Autodec load failed.')
    assert_equal(register.load(2), 40, 'Autodec register not decremented.')

    reset_state()
    register.store(1, 55)
    Program(['MOV C R1', 'EOP'])
    Program.run()
    assert_equal(memory.load(3), 55, 'Direct memory store failed.')


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


def test_call():
    print('Running CALL test...')
    reset_state()
    Program([
        'MOV R1 1',
        'CALL 13',
        'MOV R1 99',
        'MOV R1 2',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 2, 'CALL failed to jump to target.')
    cr_val = register.load(variable.load("CR"))
    assert_equal(cr_val, 11, 'CALL failed to save PC to CR.')


def test_ret():
    print('Running RET test...')
    reset_state()
    register.store(variable.load("CR"), 13)
    Program([
        'MOV R1 1',
        'RET 5',
        'MOV R1 99',
        'MOV R1 2',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 2, 'RET failed to jump to return address.')


def test_scan():
    print('Running SCAN test...')
    reset_state()
    variable.data["MSG"] = {0: 42, 1: 100}
    Program([
        'SCAN R1',
        'SCAN R2',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 42, 'SCAN failed to load MSG[0].')
    assert_equal(get_register('R2'), 100, 'SCAN failed to load MSG[1].')
    assert_equal(variable.data["MI"], 2, 'SCAN failed to increment MI.')


def test_addpc():
    print('Running ADDPC test...')
    reset_state()
    memory.store(30, 77)
    Program([
        'ADDPC R1 20',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 77, 'ADDPC (relative) failed.')


def test_relative_addressing():
    print('Running relative addressing test...')
    reset_state()
    memory.store(15, 88)
    Program([
        'MOV R1 (Z5)',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 88, 'Relative addressing (Z) failed.')


def test_based_addressing():
    print('Running based addressing test...')
    reset_state()
    memory.store(5, 99)
    Program([
        'MOV R1 (Y5)',
        'EOP'
    ])
    Program.run()
    assert_equal(get_register('R1'), 99, 'Based addressing (Y) failed.')


def main():
    test_alu_and_prnt()
    test_jumps()
    test_memory_addressing_modes()
    test_opcode_encoding()
    test_call()
    test_ret()
    test_scan()
    test_addpc()
    test_relative_addressing()
    test_based_addressing()
    print('All tests passed.')


if __name__ == '__main__':
    main()
