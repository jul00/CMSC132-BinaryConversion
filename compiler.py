from bin_convert import HalfPrecision, Length
from addressing import AddressingMode


class Instruction:
    """
    Represent a fixed-length instruction word.

    Instruction layout:
      - opcode_bits  : first 5 bits
      - mode_bits    : next 4 bits
      - address_bits : next 7 bits
      - operand_bits : last 16 bits
    """

    OPCODE_NAMES = {
        0: 'NOP',
        1: 'LOAD',
        2: 'STORE',
        3: 'ADD',
        4: 'SUB',
        5: 'MUL',
        6: 'DIV',
        7: 'JMP',
        8: 'JZ',
        9: 'JNZ',
        10: 'HALT'
    }

    MODE_NAMES = {
        0: 'IMMEDIATE',
        1: 'REGISTER',
        2: 'REGISTER_INDIRECT',
        3: 'DIRECT',
        4: 'INDIRECT',
        5: 'INDEXED',
        6: 'AUTOINC',
        7: 'AUTODEC',
        8: 'RELATIVE',
        9: 'BASED'
    }

    def __init__(self, word):
        if not isinstance(word, str):
            raise ValueError('Instruction word must be a bit string.')
        if len(word) != Length.instrxn:
            raise ValueError(
                f'Instruction word must be {Length.instrxn} bits, got {len(word)}.')

        self.word = word
        self.opcode_bits = word[:Length.whole]
        self.mode_bits = word[Length.whole:Length.whole + Length.opMode]
        self.address_bits = word[Length.whole + Length.opMode:
                                 Length.whole + Length.opMode + Length.opAddr]
        self.operand_bits = word[Length.whole + Length.opMode + Length.opAddr:]

        self.opcode = int(self.opcode_bits, 2)
        self.mode = int(self.mode_bits, 2)
        self.destination = int(self.address_bits, 2)
        self.mnemonic = self.OPCODE_NAMES.get(self.opcode, f'OP{self.opcode}')
        self.mode_name = self.MODE_NAMES.get(self.mode, f'MODE{self.mode}')

    def __repr__(self):
        return (f'<Instruction {self.mnemonic} mode={self.mode_name} '
                f'dest={self.destination} operand={self.operand_bits}>')

    def resolve_operand(self):
        if self.mode == 0:
            return AddressingMode.immediate(self.operand_bits)
        if self.mode == 1:
            return AddressingMode.register(self.operand_bits)
        if self.mode == 2:
            return AddressingMode.register_indirect(self.operand_bits)
        if self.mode == 3:
            return AddressingMode.direct(self.operand_bits)
        if self.mode == 4:
            return AddressingMode.indirect(self.operand_bits)
        if self.mode == 5:
            return AddressingMode.indexed(int(HalfPrecision.hpbin2dec(self.operand_bits)))
        if self.mode == 6:
            return AddressingMode.autoinc(self.operand_bits)
        if self.mode == 7:
            return AddressingMode.autodec(self.operand_bits)
        if self.mode == 8:
            return AddressingMode.relative(int(HalfPrecision.hpbin2dec(self.operand_bits)))
        if self.mode == 9:
            return AddressingMode.based(int(HalfPrecision.hpbin2dec(self.operand_bits)))

        raise ValueError(f'Unsupported addressing mode: {self.mode}')

    def get_operand_value(self):
        resolved = self.resolve_operand()
        if isinstance(resolved, tuple):
            return resolved[1]
        return resolved
