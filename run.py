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
        if instruction.opcode == 0:  # NOP
            return

        if instruction.opcode == 10:  # HALT
            self.halted = True
            return

        raise Except(
            f'Unhandled opcode {instruction.opcode} ({instruction.mnemonic})')

    def step(self):
        if self.halted:
            raise Except('Program has already halted.')

        raw_instruction = self.fetch()
        instruction = self.decode(raw_instruction)
        self.current_instruction = instruction

        try:
            self.execute(instruction)
        except Except as exc:
            self.exception = exc
            raise

        if not self.halted:
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

