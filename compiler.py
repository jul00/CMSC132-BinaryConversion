from bin_convert import HalfPrecision, Length
from storage import memory, register, variable

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
    @staticmethod
    def decodeMSG(msg):
        msg = msg.replace('-_', '\n')
        msg = msg.replace('-', ' ')
        msg = msg.replace('_', '\t')
        msg = msg.replace('minus', '-')
        msg = msg.replace('under', '_')
        return msg

    @staticmethod
    def encodeOp(operand):
        op = operand.strip().replace(',', '')
        try:
            val = float(op)
            return HalfPrecision.hpdec2bin(val)
        except ValueError:
            pass

        if op.startswith('M:'):
            return None

        if '(' in op and ')' in op:
            inner = op[op.find('(')+1:op.find(')')]
            outer = op.replace('('+inner+')', '')

            if 'Z' in inner:
                remain = inner.replace('Z', '')
                if remain.startswith('R') or remain in ('PC', 'ACC'):
                    mode = "100"
                    addr = int(variable.load(remain))
                elif remain in variable.data:
                    mode = "101"
                    addr = int(variable.load(remain))
                else:
                    val = int(remain)
                    mode = "110" if val >= 0 else "111"
                    addr = abs(val)
                return mode + Length.addZeros(addr, 7)

            if 'Y' in inner:
                remain = inner.replace('Y', '')
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
                if remain.startswith('R') or remain in ('PC', 'ACC') or remain in variable.data:
                    mode = "100"
                    disp_type = "0" if (remain.startswith('R') or remain in ('PC', 'ACC')) else "1"
                    addr = int(variable.load(remain))
                    return mode + disp_type + Length.addZeros(addr, 6)
                mode = "101"
                val = int(remain)
                sign = "0" if val >= 0 else "1"
                return mode + sign + Length.addZeros(abs(val), 6)

            if '+' in outer:
                return "110" + Length.addZeros(variable.load(inner), 7)
            if '-' in outer:
                return "111" + Length.addZeros(variable.load(inner), 7)
            if 'R' in inner or inner in ('PC', 'ACC'):
                return "001" + Length.addZeros(variable.load(inner), 7)

            return "011" + Length.addZeros(variable.load(inner), 7)

        if op in ('PC', 'ACC', 'JR', 'BR', 'XR', 'IR', 'CR') or op.startswith('R'):
            return "000" + Length.addZeros(variable.load(op), 7)
        addr = variable.load(op) if op in variable.data else int(op)
        return "010" + Length.addZeros(addr, 7)

    @staticmethod
    def encode(inst):
        parts = inst.strip().split()
        if not parts:
            return None
        op = parts[0].upper()

        if op in ("EOP", "FUNC"):
            return Length.addZeros("0", 32)
        if op == "CB":
            return Instruction.encode(f"ADD BR {parts[1]}")
        if op == "CF":
            return Instruction.encode(f"ADD BR {parts[1]}")
        if op == "CMP":
            return Instruction.encode(f"SUB JR {parts[1]}")
        if op == "ADDPC":
            return Instruction.encode(f"MOV {parts[1]} (Z{parts[2]})")
        if op == "CALL":
            return [Instruction.encode("MOV CR PC"), Instruction.encode(f"MOV PC {parts[1]}")]
        if op == "RET":
            return [Instruction.encode("MOV PC CR"), Instruction.encode(f"MOV ACC {parts[1]}")]

        opcode = ""
        for (_, _), (ew, cats) in operationCodes.items():
            if op in cats:
                opcode = ew + cats[op]
                break
        if not opcode:
            return None

        ib = "0"
        rb = "0"
        op1_code = "0" * 10
        op2_code = "0" * 10
        extra = "0" * 5

        if len(parts) > 1:
            code = Instruction.encodeOp(parts[1])
            if code:
                op1_code = code[-10:]

        if len(parts) > 2:
            code = Instruction.encodeOp(parts[2])
            if code:
                if len(code) == 16:
                    ib = "1"
                    rb = code[0]
                    op2_code = code[1:11]
                    extra = code[11:]
                else:
                    op2_code = code
                    if '(' in parts[2] and ('Y' in parts[2] or 'Z' in parts[2]):
                        rb = "1"

        return opcode + ib + op1_code + rb + op2_code + extra

    @staticmethod
    def encodeProgram(program):
        br_reg_addr = variable.load("BR")
        start_addr = int(register.load(br_reg_addr)) if br_reg_addr in register.data else 9
        instructions_list = []
        block_counter = 0
        in_multiline = False

        for line in program:
            line = line.strip()
            if not line:
                continue
            if line.startswith('z'):
                in_multiline = not in_multiline
                continue
            if in_multiline or line.startswith('x'):
                continue

            parts = line.split()
            op = parts[0].upper()
            if op in ("CB", "CF"):
                curr_addr = start_addr + len(instructions_list)
                block_reg_name = parts[1]
                register.store(variable.load(block_reg_name), curr_addr)
                encoded = Instruction.encode(line)
                instructions_list.insert(block_counter, encoded)
                block_counter += 1
            else:
                encoded = Instruction.encode(line)
                if isinstance(encoded, list):
                    instructions_list.extend(encoded)
                else:
                    instructions_list.append(encoded)

        register.store(variable.load("BR"), block_counter)
        addr = start_addr
        for encoded in instructions_list:
            memory.store(addr, encoded)
            addr += 1
