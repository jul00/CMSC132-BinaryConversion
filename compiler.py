from bin_convert import HalfPrecision, Length
from storage import memory, register, variable, Storage

# ─────────────────────────────────────────────────────────────
#  Operation lookup tables
# ─────────────────────────────────────────────────────────────

# Operations are grouped by their (Execute bit, Write bit) pair.
# Index inside each group becomes the Category Code (3-bit).
operations = {
    (1, 1): ["MOD", "ADD", "SUB", "MUL", "DIV"],   # Cat: 000,001,010,011,100
    (1, 0): ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE", "JMP"],  # Cat: 000…110
    (0, 1): ["MOV", "CALL", "RET", "SCAN"],         # Cat: 000,001,010,011
    (0, 0): ["PRNT", "EOP", "FUNC"],                # Cat: 000,001,001
}

# operationCodes[group_key] = (execute_write_bits, {op_name: category_code})
operationCodes = {}
for (ex, wr), ops in operations.items():
    ew_bits = str(ex) + str(wr)           # e.g. "11", "10", "01", "00"
    cat_map = {}
    for idx, op in enumerate(ops):
        cat_map[op] = format(idx, "03b")  # 3-bit category code string
    operationCodes[(ex, wr)] = (ew_bits, cat_map)


# ─────────────────────────────────────────────────────────────
#  Addressing mode binary codes  (3-bit mode + 1-bit disp-type)
#  Used in encodeOp to build the 4-bit mode portion of an operand
# ─────────────────────────────────────────────────────────────
ADDR_REGISTER        = "000"
ADDR_REG_INDIRECT    = "001"
ADDR_DIRECT          = "010"
ADDR_INDIRECT        = "011"
ADDR_INDEXED_VAR     = "100"   # displacement from register/memory
ADDR_INDEXED_INT     = "101"   # integer displacement
ADDR_AUTOINC         = "110"
ADDR_AUTODEC         = "111"


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


    # ──────────────────────────────────────────────────────────
    #  encodeProgram  –  encode all instructions into memory
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def encodeProgram(program):
        """
        Takes a list of raw instruction strings (from a source file),
        encodes each one into a 32-bit Instruction Code, and stores
        them into memory starting at the address in BR.

        CB and CF instructions are placed at the BEGINNING of the
        instruction list (before other instructions) so that block
        addresses are resolved correctly before the program runs.
        """

        # Address where instructions start (value stored in BR register)
        start_addr = int(register.load(variable.load("BR")))

        # We'll build the final ordered list here.
        # CB/CF go at the front; everything else goes at the back.
        ordered_instructions = []

        # block_counter tracks how many CB/CF we've inserted
        # so new ones go after existing CB/CF entries
        block_counter = 0

        # Tracks whether we're inside a multiline comment (z...z)
        in_multiline_comment = False

        for raw_line in program:
            line = raw_line.strip()

            # ── Skip empty lines ──────────────────────────────
            if not line:
                continue

            # ── Multiline comment handling  (z...z) ──────────
            if line[0] == "z":
                in_multiline_comment = not in_multiline_comment
                continue  # the 'z' line itself is skipped

            if in_multiline_comment:
                continue  # skip lines inside z...z block

            # ── Single-line comment  (starts with x) ─────────
            if line[0] == "x":
                continue

            # ── Optional: store message if instruction has M: ─
            # (handled inside encodeOp, nothing extra needed here)

            # ── Encode the instruction ────────────────────────
            parts = line.split()
            operation = parts[0].upper()

            encoded = Instruction.encode(line)

            # encode() may return a list (for CALL/RET expansions)
            # or a single string
            if isinstance(encoded, list):
                encoded_list = encoded
            else:
                encoded_list = [encoded]

            # ── CB or CF  →  insert at front, update block register ──
            if operation in ("CB", "CF"):
                # The current address for this block instruction
                block_addr = start_addr + block_counter

                # Store the block address into the block operand register
                # The operand (e.g. 'B3' or 'F1') is parts[1]
                block_reg_addr = variable.load(parts[1])
                hp_addr = HalfPrecision.hpdec2bin(block_addr)
                register.store(block_reg_addr, hp_addr)

                # Insert into the front section
                for enc in encoded_list:
                    ordered_instructions.insert(block_counter, enc)
                    block_counter += 1

            else:
                # Regular instructions go at the end
                for enc in encoded_list:
                    ordered_instructions.append(enc)

        # ── Store the number of blocks into BR ────────────────
        # This tells the runtime how many block instructions are at the front
        register.store(variable.load("BR"), block_counter)

        # ── Write all encoded instructions into memory ────────
        addr = start_addr
        for enc in ordered_instructions:
            memory.store(addr, enc)
            addr += 1