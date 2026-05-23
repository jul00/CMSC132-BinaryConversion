from bin_convert import HalfPrecision, Length
from storage import memory, register, variable, Storage

# ─────────────────────────────────────────────────────────────
#  Operation lookup tables
# ─────────────────────────────────────────────────────────────

# Operations mapped to their (Execute, Write) pair with explicit
# Category Codes so shared codes work (e.g. CB/CF share ADD's 001).
operations = {
    (1, 1): {
        "MOD": "000",
        "ADD": "001",
        "CB":  "001",
        "CF":  "001",
        "SUB": "010",
        "CMP": "010",
        "MUL": "011",
        "DIV": "100",
    },
    (1, 0): {
        "JEQ": "000",
        "JNE": "001",
        "JLT": "010",
        "JLE": "011",
        "JGT": "100",
        "JGE": "101",
        "JMP": "110",
    },
    (0, 1): {
        "MOV":   "000",
        "ADDPC": "000",
        "CALL":  "001",
        "RET":   "010",
        "SCAN":  "011",
    },
    (0, 0): {
        "PRNT": "000",
        "EOP":  "001",
        "FUNC": "001",
    },
}

# operationCodes[group_key] = (execute_write_bits, {op_name: category_code})
operationCodes = {}
for (ex, wr), cat_map in operations.items():
    ew_bits = str(ex) + str(wr)
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

    @staticmethod
    def decodeMSG(msg):
        msg = msg.replace('-_', '\n')
        msg = msg.replace('-', ' ')
        msg = msg.replace('_', '\t')
        msg = msg.replace('minus', '-')
        msg = msg.replace('under', '_')
        return msg

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

        if self.ib == '1' or self.rb == '1':
            hp_bits = self.ib + self.op2_bits + self.extra_bits
            return HalfPrecision.hpbin2dec(hp_bits)

        mode = self.op2_mode
        addr = self.op2_addr

        if self.rb == '1':
            if mode in ('000', '100'):
                return register.load(addr)
            if mode in ('001', '101'):
                return memory.load(addr)
            if mode == '010':
                return addr
            if mode == '011':
                return -addr
            if mode == '110':
                return addr
            if mode == '111':
                return -addr

        if mode == '000':
            return register.load(addr)
        if mode == '001':
            return memory.load(register.load(addr))
        if mode == '010':
            return memory.load(addr)
        if mode == '011':
            return memory.load(memory.load(addr))
        if mode in ('100', '101'):
            xr_val = register.load(int(variable.load("XR")))
            return memory.load(int(xr_val) + addr)
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

    @staticmethod
    def encodeOpcode(operation):
        operation = operation.upper()
        for (ex, wr), (ew_bits, cat_map) in operationCodes.items():
            if operation in cat_map:
                return ew_bits + cat_map[operation]
        raise ValueError(f'Unknown operation: {operation}')

    @staticmethod
    def encodeOperand(operand):
        op = operand.strip().replace(',', '')
        op_upper = op.upper()

        try:
            value = int(op) if '.' not in op else float(op)
            return HalfPrecision.hpdec2bin(value)
        except ValueError:
            pass

        if op_upper.startswith('M:'):
            return None

        if '(' in op_upper and ')' in op_upper:
            p_open = op_upper.index('(')
            p_close = op_upper.index(')')
            inner = op_upper[p_open+1:p_close]
            outer = op_upper[:p_open] + op_upper[p_close+1:]

            if inner.startswith('Z'):
                remain = inner[1:]
                mode = '100' if Instruction._is_reg(remain) else \
                       '101' if Instruction._is_mem(remain) else \
                       '110' if int(remain) >= 0 else '111'
                return mode + '0' + Length.addZeros(
                    abs(Instruction._resolve_value(remain)), 6)
            if inner.startswith('Y'):
                remain = inner[1:]
                mode = '000' if Instruction._is_reg(remain) else \
                       '001' if Instruction._is_mem(remain) else \
                       '010' if int(remain) >= 0 else '011'
                return mode + '0' + Length.addZeros(
                    abs(Instruction._resolve_value(remain)), 6)
            if inner.startswith('X'):
                remain = inner[1:]
                try:
                    val = int(remain)
                    sign = '0' if val >= 0 else '1'
                    mode = '101'
                    return mode + sign + Length.addZeros(abs(val), 6)
                except ValueError:
                    pass
                disp = '0' if Instruction._is_reg(remain) else '1'
                mode = '100'
                return mode + disp + Length.addZeros(
                    Instruction._resolve_value(remain), 6)

            if '+' in outer:
                return ADDR_AUTOINC + Length.addZeros(
                    Instruction._resolve_value(inner), Length.opAddr)
            if '-' in outer:
                return ADDR_AUTODEC + Length.addZeros(
                    Instruction._resolve_value(inner), Length.opAddr)
            if any(inner.startswith(r) for r in ('R','P','C','A','B','D','E','F','G','H','I','J')):
                return ADDR_REG_INDIRECT + Length.addZeros(
                    Instruction._resolve_value(inner), Length.opAddr)
            return ADDR_INDIRECT + Length.addZeros(
                Instruction._resolve_value(inner), Length.opAddr)

        if any(op_upper.startswith(r) for r in ('R','P','C','A','B','D','E','F','G','H','I','J')):
            return ADDR_REGISTER + Length.addZeros(
                Instruction._resolve_value(op_upper), Length.opAddr)
        return ADDR_DIRECT + Length.addZeros(
            Instruction._resolve_value(op_upper), Length.opAddr)

    @staticmethod
    def _is_reg(token):
        t = token.upper()
        return any(t.startswith(r) for r in ('R','P','C','I','J')) and not t.startswith('PC')

    @staticmethod
    def _is_mem(token):
        t = token.upper()
        return any(t.startswith(c) for c in ('A','B','D','E','F','G','H'))

    @staticmethod
    def _resolve_value(token):
        token = token.upper()
        if token.startswith('R') and token[1:].isdigit():
            return int(variable.load(token))
        if token in variable.data:
            return int(variable.load(token))
        try:
            return int(token)
        except ValueError:
            raise ValueError(f'Unknown operand token: {token}')

    @staticmethod
    def resolve_address(token):
        token = token.upper()
        if token.startswith('R') and token[1:].isdigit():
            addr_value = variable.load(token)
        elif token in variable.data:
            addr_value = variable.load(token)
        else:
            raise ValueError(f'Unknown operand address: {token}')

        if isinstance(addr_value, str):
            return int(HalfPrecision.hpbin2dec(addr_value))
        return int(addr_value)

    @staticmethod
    def encode(line):
        parts = line.strip().split()
        if not parts:
            raise ValueError('Empty instruction line.')

        op = parts[0].upper()

        if op == 'EOP':
            return '0' * Length.instrxn
        if op == 'FUNC':
            return '0' * Length.instrxn

        if op == 'CB':
            return Instruction.encode('ADD BR ' + parts[1])
        if op == 'CF':
            return Instruction.encode('ADD BR ' + parts[1])
        if op == 'CMP':
            return Instruction.encode('SUB JR ' + parts[1])

        if op == 'CALL':
            return [
                Instruction.encode('MOV CR PC'),
                Instruction.encode('MOV PC ' + parts[1]),
            ]

        if op == 'RET':
            return [
                Instruction.encode('MOV PC CR'),
                Instruction.encode('MOV ACC ' + parts[1]),
            ]

        if op == 'ADDPC':
            return Instruction.encode('MOV ' + ' '.join(parts[1:]))

        opcode = Instruction.encodeOpcode(op)
        if len(parts) < 2:
            raise ValueError(f'Instruction {op} requires operands.')

        dest_token = parts[1].replace(',', '')
        dest_code = Instruction.encodeOperand(dest_token)
        dest_bits = dest_code

        op2_bits = '0' * 10
        extra_bits = '0' * 5
        rb = '0'
        ib = '0'

        if len(parts) > 2:
            src_token = parts[2].replace(',', '')
            src_code = Instruction.encodeOperand(src_token)

            if src_code is None:
                pass
            elif len(src_code) == Length.precision:
                ib = src_code[0]
                rb = '1'
                op2_bits = src_code[1:11]
                extra_bits = src_code[11:]
            else:
                ib = '0'
                op2_bits = src_code
                extra_bits = '0' * 5
                src_upper = src_token.upper()
                if '(' in src_upper and ('Z' in src_upper or 'Y' in src_upper):
                    rb = '1'

        return opcode + ib + dest_bits + rb + op2_bits + extra_bits


    # ──────────────────────────────────────────────────────────
    #  encodeProgram  –  encode all instructions into memory
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def encodeProgram(program, start_addr=None):
        """
        Takes a list of raw instruction strings (from a source file),
        encodes each one into a 32-bit Instruction Code, and stores
        them into memory starting at the given address (or the
        address in BR if not specified).

        CB and CF instructions are placed at the BEGINNING of the
        instruction list (before other instructions) so that block
        addresses are resolved correctly before the program runs.
        """

        # Address where instructions start
        if start_addr is None:
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