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

    # ──────────────────────────────────────────────────────────
    #  decodeMSG
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def decodeMSG(msg):
        """
        Converts special escape sequences inside a message string
        back to their real characters.

        Rules (applied in order):
          -_   →  newline   (must come before single - and _ checks)
          -    →  space
          _    →  tab
          minus  →  -
          under  →  _
        """
        msg = msg.replace("-_", "\n")   # dash+underscore  → newline
        msg = msg.replace("-",  " ")    # dash alone       → space
        msg = msg.replace("_",  "\t")   # underscore alone → tab
        msg = msg.replace("minus", "-") # word 'minus'     → dash
        msg = msg.replace("under", "_") # word 'under'     → underscore
        return msg

    # ──────────────────────────────────────────────────────────
    #  encodeOp  –  convert one operand string to a 10-bit code
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def encodeOp(operand):
        """
        Converts a human-readable operand (e.g. 'R1', '(R2)', '3.5',
        '(XR+)', '(B1Z)') into a 10-bit binary string:
            [3-bit addressing mode][7-bit address/value]

        Special case – Immediate:
            If the operand is a plain number, return its 16-bit
            Half Precision binary (used differently by encode()).

        Special case – Message 'M:...':
            Stores the message text and returns None (optional feature).
        """

        operand = str(operand).strip()

        # ── 1. IMMEDIATE  (plain number) ──────────────────────
        try:
            num = float(operand)
            # Return the full 16-bit HP binary; encode() will place
            # this in the Extra bits field with ib=1.
            return HalfPrecision.hpdec2bin(num).zfill(Length.precision)
        except ValueError:
            pass  # not a number → keep going

        # ── 2. MESSAGE  'M:some_text' ─────────────────────────
        if operand.startswith("M:"):
            msg_text = Instruction.decodeMSG(operand[2:])
            # Store message in the special MSG dictionary
            msg_index = variable.data["MI"]
            variable.data["MSG"][msg_index] = msg_text
            variable.data["MI"] += 1
            # Messages are handled outside ISA encoding
            return None

        # ── 3. OPERANDS WITH PARENTHESES  e.g. (R1), (XR+), (B2Z) ──
        if "(" in operand and ")" in operand:
            # Strip the parentheses
            inner = operand.replace("(", "").replace(")", "")

            # ── 3a. Indexed / Based / Relative  (contain X, Y, or Z) ──
            if "X" in inner or "Y" in inner or "Z" in inner:
                if   "Z" in inner:
                    mode_prefix = "1"          # Relative
                    inner = inner.replace("Z", "")
                elif "Y" in inner:
                    mode_prefix = "01"         # Based  (rb handled in encode)
                    inner = inner.replace("Y", "")
                else:  # X
                    mode_prefix = ""           # Indexed (mode bits set below)
                    inner = inner.replace("X", "")

                # What remains is either an integer, a register (contains R/PC/ACC),
                # or a memory address (pure digits treated as memory)
                try:
                    # Integer displacement
                    disp_val = int(inner)
                    if disp_val >= 0:
                        disp_type = "0"
                    else:
                        disp_type = "1"
                        disp_val = abs(disp_val)
                    addr_bits = format(disp_val, "06b")   # 6-bit displacement

                    if mode_prefix == "":
                        # Indexed with integer displacement
                        mode = ADDR_INDEXED_INT
                    else:
                        mode = mode_prefix  # Relative or Based (caller sets rb)

                    return (mode + disp_type + addr_bits).zfill(Length.operand)

                except ValueError:
                    # Register or memory variable displacement
                    is_register = (
                        inner.startswith("R") or
                        inner in ("PC", "ACC", "XR", "BR", "IR", "JR", "CR")
                    )
                    disp_type = "0" if is_register else "1"
                    addr = variable.load(inner)          # numeric address
                    addr_bits = format(int(addr), "06b") # 6-bit

                    if mode_prefix == "":
                        mode = ADDR_INDEXED_VAR
                    else:
                        mode = mode_prefix

                    return (mode + disp_type + addr_bits).zfill(Length.operand)

            # ── 3b. Auto-increment  e.g. (R3+) ───────────────
            elif "+" in inner:
                inner = inner.replace("+", "")
                mode = ADDR_AUTOINC

            # ── 3c. Auto-decrement  e.g. (R3-) ───────────────
            elif "-" in inner:
                inner = inner.replace("-", "")
                mode = ADDR_AUTODEC

            # ── 3d. Register-indirect or Indirect ─────────────
            elif (inner.startswith("R") or
                  inner in ("PC", "ACC", "XR", "BR", "IR", "JR", "CR")):
                mode = ADDR_REG_INDIRECT
            else:
                mode = ADDR_INDIRECT  # indirect via memory address

            # Get the numeric address from the variable table
            addr = variable.load(inner)
            addr_bits = format(int(addr), "07b")   # 7-bit address
            return (mode + addr_bits).zfill(Length.operand)

        # ── 4. NO PARENTHESES  –  Register or Direct ─────────
        is_register = (
            operand.startswith("R") or
            operand in ("PC", "ACC", "XR", "BR", "IR", "JR", "CR")
        )
        if is_register:
            mode = ADDR_REGISTER
        else:
            mode = ADDR_DIRECT

        addr = variable.load(operand)
        addr_bits = format(int(addr), "07b")       # 7-bit address
        return (mode + addr_bits).zfill(Length.operand)

    # ──────────────────────────────────────────────────────────
    #  encode  –  convert one instruction line to 32-bit code
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def encode(inst):
        """
        Converts a single instruction string like 'ADD R1 R2' into a
        32-bit Instruction Code binary string.

        Instruction Code layout (32 bits):
          [0]      Execute bit
          [1]      Write bit
          [2-4]    Category Code  (3 bits)
          [5]      Immediate bit (ib)
          [6-8]    Op1 Mode      (3 bits)
          [9-15]   Op1 Addr      (7 bits)
          [16]     Relative bit (rb)
          [17-19]  Op2 Mode      (3 bits)
          [20-26]  Op2 Addr      (7 bits)
          [27-31]  Extra bits    (5 bits, used for immediate value tail)
        """

        parts = inst.strip().split()
        operation = parts[0].upper()

        # ── FUNC / EOP  →  all-zero instruction ──────────────
        if operation in ("FUNC", "EOP"):
            return "0" * Length.instrxn

        # ── Initialise ib and rb to zero ─────────────────────
        ib = "0"   # immediate bit
        rb = "0"   # relative/based bit

        # ── Expand shorthand operations into primitives ───────
        # We may produce TWO instructions (e.g. CALL, RET).
        # Each expansion returns a list of encoded instruction strings.

        extra_instructions = []  # additional encoded instructions

        if operation == "CB":
            # CB B3  →  ADD BR B3   (adds BR to block address)
            operand1 = "BR"
            operand2 = parts[1]
            operation = "ADD"
            parts = ["ADD", operand1, operand2]

        elif operation == "CF":
            # CF F2  →  ADD BR F2
            operand1 = "BR"
            operand2 = parts[1]
            operation = "ADD"
            parts = ["ADD", operand1, operand2]

        elif operation == "CMP":
            # CMP R1  →  SUB JR R1
            operation = "SUB"
            parts = ["SUB", "JR", parts[1]]

        elif operation in ("JEQ","JNE","JLT","JLE","JGT","JGE","JMP"):
            # J** B3  →  compare JR to 0, then jump
            # Encoded as a jump; condition held in category code
            pass  # category code already encodes the condition

        elif operation == "ADDPC":
            # ADDPC dest op2  →  MOV dest (op2 relative)
            operation = "MOV"
            # op2 stays as-is; encode() will handle it

        elif operation == "CALL":
            # CALL F2 →
            #   1. MOV CR PC        (save current PC to CR)
            #   2. MOV PC F2        (jump to function block)
            mov_cr_pc = Instruction.encode("MOV CR PC")
            extra_instructions.append(mov_cr_pc)
            operation = "MOV"
            parts = ["MOV", "PC", parts[1]]

        elif operation == "RET":
            # RET R1 →
            #   1. MOV PC CR        (return to caller)
            #   2. MOV ACC R1       (put return value in ACC)
            mov_pc_cr = Instruction.encode("MOV PC CR")
            extra_instructions.append(mov_pc_cr)
            operation = "MOV"
            parts = ["MOV", "ACC", parts[1]]

        # ── Build OpCode ──────────────────────────────────────
        opcode = None
        for (ex, wr), (ew_bits, cat_map) in operationCodes.items():
            if operation in cat_map:
                opcode = ew_bits + cat_map[operation]  # 5-bit opcode
                break

        if opcode is None:
            raise ValueError(f"Unknown operation: {operation}")

        # ── Encode operands ───────────────────────────────────
        op1_encoded = ""
        op2_encoded = ""
        extra_bits  = "0" * 5   # bits 27-31

        # Operand 1
        if len(parts) > 1:
            op1_encoded = Instruction.encodeOp(parts[1])

        # Operand 2
        if len(parts) > 2:
            op2_raw = Instruction.encodeOp(parts[2])

            # Check if operand 2 is Immediate (16-bit HP binary returned)
            if op2_raw is not None and len(op2_raw) == Length.precision:
                ib = "1"
                # The HP binary goes into bits 17-31 (15 bits).
                # We take the last 15 bits of the 16-bit HP value.
                hp_val = op2_raw
                op2_mode_bits = "000"               # mode field (bits 17-19)
                op2_addr_bits = hp_val[:7]           # bits 20-26
                extra_bits    = hp_val[7:12]         # bits 27-31  (5 bits)
                op2_encoded   = op2_mode_bits + op2_addr_bits
            else:
                # Check if it's Relative or Based (rb=1)
                # encodeOp returns a mode prefix of "1xx" for relative,
                # "01x" for based — we detect by checking the mode nibble.
                if op2_raw is not None:
                    mode_nibble = op2_raw[:4]
                    # Relative modes start with "1" in our encoding above
                    # Based modes start with "01"
                    # We set rb=1 for both; they are distinguished by mode bits
                    if mode_nibble[0] == "1" or mode_nibble[:2] == "01":
                        rb = "1"
                op2_encoded = op2_raw if op2_raw else "0" * Length.operand

        # ── Assemble the 32-bit instruction ───────────────────
        #
        #  opcode      = 5 bits  (bits 0-4)
        #  ib          = 1 bit   (bit  5)
        #  op1_encoded = 10 bits (bits 6-15)  [3-bit mode + 7-bit addr]
        #  rb          = 1 bit   (bit  16)
        #  op2_encoded = 10 bits (bits 17-26) [3-bit mode + 7-bit addr]
        #  extra_bits  = 5 bits  (bits 27-31)
        #
        # Pad missing fields with zeros
        op1_encoded = op1_encoded.zfill(Length.operand) if op1_encoded else "0" * Length.operand
        op2_encoded = op2_encoded.zfill(Length.operand) if op2_encoded else "0" * Length.operand

        instruction_code = opcode + ib + op1_encoded + rb + op2_encoded + extra_bits

        # Ensure exactly 32 bits
        instruction_code = instruction_code.zfill(Length.instrxn)

        # If there were extra instructions (CALL/RET), return them joined
        if extra_instructions:
            return extra_instructions + [instruction_code]

        return instruction_code

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