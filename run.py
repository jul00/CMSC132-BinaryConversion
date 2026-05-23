# =============================================================
#  run.py
#  Johann's part  → Except class  (top of the file)
#  Julo's part    → Program class (will be added below)
# =============================================================

from bin_convert import HalfPrecision, Length
from storage import memory, register, variable
from addressing import Access, AddressingMode


# ─────────────────────────────────────────────────────────────
#  Except
#  A simple container that describes an exception (error)
#  that can happen during program execution.
#
#  Think of it like a custom error report card:
#    - What went wrong? (message)
#    - Did it actually happen? (occur)
#    - What should be returned instead? (ret)
# ─────────────────────────────────────────────────────────────
class Except(Exception):

    def __init__(self, msg, occur=True):
        """
        Create a new exception.

        Parameters:
            msg   – a string describing the error
                    e.g. "Division by zero!"
            occur – True if the exception actually happened,
                    False if it is just a placeholder (default: True)
        """
        self.message = msg   # The error description
        self.occur   = occur # Did this exception actually happen?
        self.ret     = None  # Optional: a value to return instead of crashing


    def dispMSG(self):
        """
        Print the exception message to the screen.
        Call this when you want to show the error to the user.
        """
        print(self.message)


    def isOccur(self):
        """
        Check whether this exception actually happened.

        Returns:
            True  → the exception occurred (something went wrong)
            False → no exception, everything is fine
        """
        return self.occur


    def setReturn(self, value):
        """
        Store a special return value for this exception.

        Used when the program should return something meaningful
        instead of just crashing. For example:
          - Division of 0 / 0  → return 'Infinity'
          - Division of x / 0  → return 'undefined'

        Parameters:
            value – the value to return when this exception happens
        """
        self.ret = value


    def getReturn(self):
        """
        Retrieve the special return value for this exception.

        Returns:
            Whatever was set by setReturn() — e.g. 'Infinity' or 'undefined'
        """
        return self.ret


class Instruction:
    """Parse a 32-bit instruction word for runtime execution."""

    OPCODE_NAMES = {
        (0, 0, 0): 'PRNT',
        (0, 0, 1): 'EOP',
        (0, 0, 2): 'FUNC',
        (0, 1, 0): 'MOV',
        (0, 1, 1): 'CALL',
        (0, 1, 2): 'RET',
        (0, 1, 3): 'SCAN',
        (1, 1, 0): 'MOD',
        (1, 1, 1): 'ADD',
        (1, 1, 2): 'SUB',
        (1, 1, 3): 'MUL',
        (1, 1, 4): 'DIV',
        (1, 0, 0): 'JEQ',
        (1, 0, 1): 'JNE',
        (1, 0, 2): 'JLT',
        (1, 0, 3): 'JLE',
        (1, 0, 4): 'JGT',
        (1, 0, 5): 'JGE',
        (1, 0, 6): 'JMP',
    }

    MODE_NAMES = {
        '000': 'REGISTER',
        '001': 'REGISTER_INDIRECT',
        '010': 'DIRECT',
        '011': 'INDIRECT',
        '100': 'INDEXED_VAR',
        '101': 'INDEXED_INT',
        '110': 'AUTOINC',
        '111': 'AUTODEC',
    }

    def __init__(self, word):
        if not isinstance(word, str):
            raise ValueError('Instruction word must be a bit string.')
        if len(word) != Length.instrxn:
            raise ValueError(
                f'Instruction word must be {Length.instrxn} bits, got {len(word)}.')

        self.raw = word
        self.opcode_bits = word[:5]
        self.ib = word[5]
        self.op1_bits = word[6:16]
        self.rb = word[16]
        self.op2_bits = word[17:27]
        self.extra_bits = word[27:32]

        if word == '0' * Length.instrxn:
            self.opcode = 0
            self.mnemonic = 'EOP'
            self.op1_mode = '000'
            self.op1_addr = 0
            self.op2_mode = '000'
            self.op2_addr = 0
            self.destination = 0
            return

        ex = int(self.opcode_bits[0], 2)
        wr = int(self.opcode_bits[1], 2)
        cat = int(self.opcode_bits[2:], 2)
        self.opcode = int(self.opcode_bits, 2)
        self.opcode_tuple = (ex, wr, cat)
        self.mnemonic = self.OPCODE_NAMES.get(self.opcode_tuple, 'UNKNOWN')

        self.op1_mode = self.op1_bits[:3]
        self.op1_addr = int(self.op1_bits[3:], 2)
        self.op2_mode = self.op2_bits[:3]
        self.op2_addr = int(self.op2_bits[3:], 2)
        self.destination = self.op1_addr

    def __repr__(self):
        return (f'<Instruction {self.mnemonic} op1={self.op1_mode}:{self.op1_addr} '
                f'op2={self.op2_mode}:{self.op2_addr} ib={self.ib} rb={self.rb}>')

    def get_operand_value(self):
        if self.raw == '0' * Length.instrxn:
            return None

        if self.ib == '1':
            hp_bits = self.ib + self.op2_bits + self.extra_bits
            return HalfPrecision.hpbin2dec(hp_bits)

        mode = self.op2_mode
        addr = self.op2_addr

        if mode == '000':
            return register.load(addr)
        if mode == '001':
            return memory.load(register.load(addr))
        if mode == '010':
            return memory.load(addr)
        if mode == '011':
            return memory.load(memory.load(addr))
        if mode == '110':
            mem_addr = register.load(addr)
            value = memory.load(mem_addr)
            register.store(addr, mem_addr + 1)
            return value
        if mode == '111':
            mem_addr = register.load(addr) - 1
            register.store(addr, mem_addr)
            return memory.load(mem_addr)

        raise ValueError(f'Unsupported operand mode: {mode}')


# =============================================================
#  Julo adds the Program class below this line
# =============================================================


class Program:

    def __init__(self, start_address=None, max_steps=1000):
        self.start_address = (
            start_address if start_address is not None
            else Access.data('PC', ['var', 'reg']))
        self.max_steps = max_steps
        self.halted = False
        self.current_instruction = None
        self.exception = Except('No exception', occur=False)
        self.steps = 0
        self.reset()

    def reset(self, pc=None):
        self.halted = False
        self.steps = 0
        self.current_instruction = None
        self.exception = Except('No exception', occur=False)
        self.write_pc(pc if pc is not None else self.start_address)

    def read_pc(self):
        return Access.data('PC', ['var', 'reg'])

    def write_pc(self, value):
        Access.store('reg', variable.load('PC'), value)

    def fetch(self):
        pc = int(self.read_pc())
        raw_instruction = memory.load(pc)
        Access.store('reg', variable.load('IR'), raw_instruction)
        return raw_instruction

    def decode(self, raw_instruction):
        return Instruction(raw_instruction)

    def execute(self, instruction):
        if instruction.raw == '0' * Length.instrxn or instruction.mnemonic == 'EOP':
            self.halted = True
            return False

        operand = instruction.get_operand_value()
        dest = instruction.destination

        if instruction.opcode == 0:  # NOP
            return False

        if instruction.opcode == 1:  # LOAD
            Access.store('reg', dest, operand)
            return False

        if instruction.opcode == 2:  # STORE
            Access.store('mem', dest, operand)
            return False

        if instruction.opcode == 3:  # ADD
            current = register.load(dest)
            result = current + operand
            Access.store('reg', dest, result)
            return False

        if instruction.opcode == 4:  # SUB
            current = register.load(dest)
            result = current - operand
            Access.store('reg', dest, result)
            return False

        if instruction.opcode == 5:  # MUL
            current = register.load(dest)
            result = current * operand
            Access.store('reg', dest, result)
            return False

        if instruction.opcode == 6:  # DIV
            current = register.load(dest)
            if operand == 0:
                raise Except('Division by zero!')
            result = current / operand
            Access.store('reg', dest, result)
            return False

        if instruction.opcode == 7:  # JMP
            self.write_pc(int(operand))
            return True

        if instruction.opcode == 8:  # JZ
            test_value = register.load(dest)
            if test_value == 0:
                self.write_pc(int(operand))
                return True
            return False

        if instruction.opcode == 9:  # JNZ
            test_value = register.load(dest)
            if test_value != 0:
                self.write_pc(int(operand))
                return True
            return False

        if instruction.opcode == 10:  # HALT
            self.halted = True
            return False

        raise Except(
            f'Unhandled opcode {instruction.opcode} ({instruction.mnemonic})')

    def step(self):
        if self.halted:
            raise Except('Program has already halted.')

        raw_instruction = self.fetch()
        instruction = self.decode(raw_instruction)
        self.current_instruction = instruction

        try:
            pc_changed = self.execute(instruction)
        except Except as exc:
            self.exception = exc
            raise

        if not self.halted and not pc_changed:
            self.write_pc(self.read_pc() + 1)

        self.steps += 1
        return instruction

    def run(self, max_steps=None):
        limit = self.max_steps if max_steps is None else max_steps
        while not self.halted and self.steps < limit:
            try:
                self.step()
            except Except:
                break
        return self

    def load_program(self, instructions, start_address=None):
        address = (
            self.start_address if start_address is None
            else start_address)
        for instruction in instructions:
            raw = instruction.word if hasattr(instruction, 'word') else instruction
            if not isinstance(raw, str):
                raise ValueError('Program.load_program expects instruction bitstrings or Instruction objects.')
            Access.store('mem', address, raw)
            address += 1

    def get_register(self, name):
        register_address = variable.load(name)
        return register.load(int(register_address))

    def set_register(self, name, value):
        register_address = variable.load(name)
        Access.store('reg', int(register_address), value)

    def dump_state(self):
        print('Program state:')
        print(f'  PC = {self.read_pc()}')
        print(f'  Halted = {self.halted}')
        print(f'  Steps = {self.steps}')
        if self.current_instruction is not None:
            print(f'  Current instruction = {self.current_instruction}')
        if self.exception is not None and self.exception.isOccur():
            print(f'  Exception = {self.exception.message}')

