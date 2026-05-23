# =============================================================
#  run.py
#  Johann's part  → Except class  (top of the file)
#  Julo's part    → Program class (will be added below)
# =============================================================

from bin_convert import HalfPrecision, Length
from storage import memory, register, variable
from addressing import Access, AddressingMode
from compiler import Instruction


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
class Program:

    def __init__(self, program=None, start_address=None, max_steps=1000):
        self.start_address = (
            start_address if start_address is not None
            else Access.data('PC', ['var', 'reg']))
        self.max_steps = max_steps
        self.halted = False
        self.current_instruction = None
        self.exception = Except('No exception', occur=False)
        self.steps = 0
        self.reset()
        if program is not None:
            self.encode_program(program)

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

    @staticmethod
    def exception(name, value):
        if name == 'DivByZero':
            op1, op2 = value
            exc = Except('Division by zero!')
            if op2 == 0:
                exc.setReturn('Infinity' if op1 == 0 else 'undefined')
            return exc
        return Except('No exception', occur=False)

    def encode_program(self, program):
        Instruction.encodeProgram(program, start_addr=int(self.start_address))

    def write(self, dest, src, movecode=0):
        if movecode == 1:
            Access.store('reg', variable.load('CR'), self.read_pc())
        elif movecode == 2:
            self.write_pc(register.load(variable.load('CR')))
        if isinstance(dest, tuple):
            typ, addr = dest
            Access.store(typ, addr, src)
        else:
            raise ValueError('Invalid write destination')

    def getOp(self, mode, addr):
        hp_addr = HalfPrecision.hpdec2bin(addr)
        if mode == '000':
            effective, value, _ = AddressingMode.register(hp_addr)
            return ('reg', effective, value)
        if mode == '001':
            effective, value = AddressingMode.register_indirect(hp_addr)
            return ('mem', effective, value)
        if mode == '010':
            effective, value = AddressingMode.direct(hp_addr)
            return ('mem', effective, value)
        if mode == '011':
            effective, value = AddressingMode.indirect(hp_addr)
            return ('mem', effective, value)
        if mode == '100' or mode == '101':
            effective, value = AddressingMode.indexed(addr)
            return ('mem', effective, value)
        if mode == '110':
            effective, value = AddressingMode.autoinc(hp_addr)
            return ('mem', effective, value)
        if mode == '111':
            effective, value = AddressingMode.autodec(hp_addr)
            return ('mem', effective, value)
        raise ValueError(f'Unsupported operand mode: {mode}')

    def execute(self, instruction):
        if instruction.raw == '0' * Length.instrxn or instruction.mnemonic in ('EOP', 'FUNC'):
            self.halted = True
            return False

        mnemonic = instruction.mnemonic
        op1 = self.getOp(instruction.op1_mode, instruction.op1_addr)
        op2_value = instruction.get_operand_value()

        if mnemonic == 'MOV':
            self.write((op1[0], op1[1]), op2_value)
            return False

        if mnemonic == 'PRNT':
            # If no explicit second operand was encoded, print op1.
            no_second = (
                instruction.op2_bits == '0' * 10 and
                instruction.extra_bits == '0' * 5 and
                instruction.rb == '0' and
                instruction.ib == '0'
            )
            val = op1[2] if no_second else op2_value
            print(val)
            return False

        if mnemonic == 'ADD':
            result = op1[2] + op2_value
            self.write((op1[0], op1[1]), result)
            return False

        if mnemonic == 'SUB':
            result = op1[2] - op2_value
            self.write((op1[0], op1[1]), result)
            return False

        if mnemonic == 'MUL':
            result = op1[2] * op2_value
            self.write((op1[0], op1[1]), result)
            return False

        if mnemonic == 'DIV':
            if op2_value == 0:
                raise Program.exception('DivByZero', (op1[2], op2_value))
            result = op1[2] / op2_value
            self.write((op1[0], op1[1]), result)
            return False

        if mnemonic == 'JMP':
            self.write_pc(int(op1[2]))
            return True

        if mnemonic == 'JEQ':
            jr = register.load(variable.load('JR'))
            if jr == 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'JNE':
            jr = register.load(variable.load('JR'))
            if jr != 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'JLT':
            jr = register.load(variable.load('JR'))
            if jr < 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'JLE':
            jr = register.load(variable.load('JR'))
            if jr <= 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'JGT':
            jr = register.load(variable.load('JR'))
            if jr > 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'JGE':
            jr = register.load(variable.load('JR'))
            if jr >= 0:
                self.write_pc(int(op1[2]))
                return True
            return False

        if mnemonic == 'CALL':
            self.write((op1[0], op1[1]), op2_value, movecode=1)
            return True

        if mnemonic == 'RET':
            self.write((op1[0], op1[1]), op2_value, movecode=2)
            return True

        if mnemonic == 'SCAN':
            self.write((op1[0], op1[1]), op2_value, movecode=3)
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


if __name__ == '__main__':
    div_exc = Except('Division by zero', occur=False)
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
        Program(lines).run()

