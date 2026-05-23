from bin_convert import HalfPrecision, Length
from storage import memory, register, variable

# ─────────────────────────────────────────────────────────────
#  Global variables for operations and codes (as per Requirement V)
# ─────────────────────────────────────────────────────────────

# Grouped by Execute (bit 0) and Write (bit 1)
operations = {
    (1, 1): ["MOD", "ADD", "CB", "CF", "SUB", "CMP", "MUL", "DIV"],
    (1, 0): ["JEQ", "JNE", "JLT", "JLE", "JGT", "JGE", "JMP"],
    (0, 1): ["MOV", "ADDPC", "CALL", "RET", "SCAN"],
    (0, 0): ["PRNT", "EOP", "FUNC"]
}

# Mapping: (Execute, Write) -> (E+W bits, {Op: Category})
operationCodes = {
    (1, 1): ("11", {"MOD": "000", "ADD": "001", "CB": "001", "CF": "001", "SUB": "010", "CMP": "010", "MUL": "011", "DIV": "100"}),
    (1, 0): ("10", {"JEQ": "000", "JNE": "001", "JLT": "010", "JLE": "011", "JGT": "100", "JGE": "101", "JMP": "110"}),
    (0, 1): ("01", {"MOV": "000", "ADDPC": "000", "CALL": "001", "RET": "010", "SCAN": "011"}),
    (0, 0): ("00", {"PRNT": "000", "EOP": "001", "FUNC": "001"})
}

class Instruction:
    # No constructor, no attributes as per Requirement V.

    @staticmethod
    def decodeMSG(msg):
        """Requirement V.3: Decodes special character sequences in messages."""
        msg = msg.replace('-_', '\n')
        msg = msg.replace('-', ' ')
        msg = msg.replace('_', '\t')
        msg = msg.replace('minus', '-')
        msg = msg.replace('under', '_')
        return msg

    @staticmethod
    def encodeOp(operand):
        """Requirement V.4: Converts operand to 10-bit Operand Code or 16-bit HP binary."""
        op = operand.strip().replace(',', '')
        
        # Check if immediate (number)
        try:
            val = float(op)
            # Returns 16-bit Half Precision binary format
            return HalfPrecision.hpdec2bin(val)
        except ValueError:
            pass

        # Check if message (optional/not required for basic ISA but mentioned)
        if op.startswith('M:'):
            # Optional: handle message storage
            return None

        # Process complex operands with parenthesis (V.4.c.alpha/beta)
        if '(' in op and ')' in op:
            inner = op[op.find('(')+1:op.find(')')]
            outer = op.replace('('+inner+')', '')
            
            # alpha: relative (Z), based (Y), indexed (X)
            if 'Z' in inner:
                remain = inner.replace('Z', '')
                # Mode logic for relative (IV.6 specifies bits 100-111 for relative if rb=1)
                # We'll return 10 bits: Mode(3) + Addr(7)
                if remain.startswith('R') or remain in ('PC', 'ACC'):
                    mode = "100" # Relative from register
                    addr = int(variable.load(remain))
                elif remain in variable.data:
                    mode = "101" # Relative from memory
                    addr = int(variable.load(remain))
                else:
                    val = int(remain)
                    mode = "110" if val >= 0 else "111"
                    addr = abs(val)
                return mode + Length.addZeros(addr, 7)
            
            if 'Y' in inner:
                remain = inner.replace('Y', '')
                # Based modes (IV.6 bits 000-011 for based if rb=1)
                if remain.startswith('R') or remain in ('PC', 'ACC'):
                    mode = "000"
                    addr = int(variable.load(remain))
                elif remain in variable.data:
                    mode = "001"
                    addr = int(variable.load(remain))
                else:
                    val = int(remain)
                    mode = "010" if val >= 0 else "011"
                    addr = abs(val)
                return mode + Length.addZeros(addr, 7)

            if 'X' in inner:
                remain = inner.replace('X', '')
                # Indexed modes (IV.3/IV.6 bits 100-101)
                if remain.startswith('R') or remain in ('PC', 'ACC') or remain in variable.data:
                    mode = "100" # displacement from register/memory
                    # leftmost signifies displacement type: 0 reg, 1 mem
                    disp_type = "0" if (remain.startswith('R') or remain in ('PC', 'ACC')) else "1"
                    addr = int(variable.load(remain))
                    return mode + disp_type + Length.addZeros(addr, 6)
                else:
                    mode = "101" # integer displacement
                    val = int(remain)
                    sign = "0" if val >= 0 else "1"
                    return mode + sign + Length.addZeros(abs(val), 6)

            # beta: auto-inc (+), auto-dec (-), register indirect (R)
            if '+' in outer:
                return "110" + Length.addZeros(variable.load(inner), 7)
            if '-' in outer:
                return "111" + Length.addZeros(variable.load(inner), 7)
            if 'R' in inner or inner in ('PC', 'ACC'):
                return "001" + Length.addZeros(variable.load(inner), 7)
            
            # Otherwise indirect
            return "011" + Length.addZeros(variable.load(inner), 7)

        # gamma: register vs direct (no parenthesis)
        if op in ('PC', 'ACC', 'JR', 'BR', 'XR', 'IR', 'CR') or op.startswith('R'):
            return "000" + Length.addZeros(variable.load(op), 7)
        else:
            # direct addressing
            addr = variable.load(op) if op in variable.data else int(op)
            return "010" + Length.addZeros(addr, 7)

    @staticmethod
    def encode(inst):
        """Requirement V.5: Encodes single instruction string to 32-bit binary."""
        parts = inst.strip().split()
        if not parts: return None
        op = parts[0].upper()
        
        # alpha: Simplify operations
        if op == "EOP" or op == "FUNC":
            return Length.addZeros("0", 32)
        
        # Simplification logic (Requirement V.5.c.alpha)
        # We handle them by re-calling encode with the simplified version
        if op == "CB":
            # Simplify to: Add 'BR' to Block
            return Instruction.encode(f"ADD BR {parts[1]}")
        if op == "CF":
            # Simplify to: Add 'BR' to Function Block
            return Instruction.encode(f"ADD BR {parts[1]}")
        if op == "CMP":
            # Simplify to: Subtract operand from 'JR'
            return Instruction.encode(f"SUB JR {parts[1]}")
        # Note: 'J' is handled in execution usually, but instructions say "Compare 'JR' to zero based on condition"
        # CALL/RET/ADDPC simplifications:
        if op == "ADDPC":
            return Instruction.encode(f"MOV {parts[1]} (Z{parts[2]})")
        if op == "CALL":
            return [Instruction.encode("MOV CR PC"),
                    Instruction.encode(f"MOV PC {parts[1]}")]
        if op == "RET":
            return [Instruction.encode("MOV PC CR"),
                    Instruction.encode(f"MOV ACC {parts[1]}")]

        # Normal encoding
        opcode = ""
        for (ex, wr), (ew, cats) in operationCodes.items():
            if op in cats:
                opcode = ew + cats[op]
                break
        
        if not opcode: return None
        
        # bits: OpCode(5) ib(1) Op1(10) rb(1) Op2(10) Extra(5)
        #
        # ib/rb overlap: The spec puts the 16-bit HalfPrecision immediate
        # across the 10-bit Op2 field + 5-bit Extra + the 1-bit rb field.
        # This means ib=1 signals immediate AND rb holds the HP sign bit (MSB).
        # When ib=0, rb acts as a normal relative/based flag.
        # The decoder handles this by checking ib first: if ib=1, reconstruct
        # the full HP as rb + op2_code + extra.
        ib = "0"
        rb = "0"
        op1_code = "0" * 10
        op2_code = "0" * 10
        extra = "0" * 5
        
        if len(parts) > 1:
            code = Instruction.encodeOp(parts[1])
            if code: op1_code = code[-10:]
            
        if len(parts) > 2:
            code = Instruction.encodeOp(parts[2])
            if code:
                if len(code) == 16: # Immediate
                    ib = "1" # Flag that Op2 is immediate
                    rb = code[0] # HP sign bit overlays rb field
                    op2_code = code[1:11]
                    extra = code[11:]
                else:
                    op2_code = code
                    if '(' in parts[2] and ('Y' in parts[2] or 'Z' in parts[2]):
                        rb = "1"
        
        return opcode + ib + op1_code + rb + op2_code + extra

    @staticmethod
    def encodeProgram(program):
        """Requirement V.6: Encodes full program and stores in memory."""
        # alpha: Initialization
        br_reg_addr = variable.load("BR")
        start_addr = int(register.load(br_reg_addr)) if br_reg_addr in register.data else 9
        
        instructions_list = []
        block_counter = 0
        in_multiline = False
        
        # beta: Loop every instruction
        for line in program:
            line = line.strip()
            if not line: continue
            
            # Skip comments
            if line.startswith('z'):
                in_multiline = not in_multiline
                continue
            if in_multiline or line.startswith('x'):
                continue
            
            parts = line.split()
            op = parts[0].upper()
            
            # gamma: CB/CF handling
            if op == "CB" or op == "CF":
                # Store current address in block register operand (parts[1])
                curr_addr = start_addr + len(instructions_list)
                block_reg_name = parts[1]
                register.store(variable.load(block_reg_name), curr_addr)
                
                # Insert at start (ith element based on block_counter)
                encoded = Instruction.encode(line)
                instructions_list.insert(block_counter, encoded)
                block_counter += 1
            else:
                # delta: others append to last
                encoded = Instruction.encode(line)
                if isinstance(encoded, list):
                    instructions_list.extend(encoded)
                else:
                    instructions_list.append(encoded)
                
        # epsilon: Store number of blocks to 'BR'
        register.store(variable.load("BR"), block_counter)
        
        # zeta: Put encoded instructions to memory starting from address of 'BR'
        addr = start_addr
        for encoded in instructions_list:
            memory.store(addr, encoded)
            addr += 1
