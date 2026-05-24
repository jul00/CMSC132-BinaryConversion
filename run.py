from bin_convert import HalfPrecision, Length
from storage import memory, register, variable
from addressing import Access, AddressingMode
from compiler import Instruction

class Except(Exception):
    def __init__(self, msg, occur=True):
        self.message = msg
        self.occur = occur
        self.ret = None

    def dispMSG(self):
        print(self.message)

    def isOccur(self):
        return self.occur

    def setReturn(self, value):
        self.ret = value

    def getReturn(self):
        return self.ret

class Program:
    def __init__(self, program):
        """Requirement VI.1: Encode each instruction of the program."""
        Instruction.encodeProgram(program)

    @staticmethod
    def exception(name, value):
        """Requirement VI.2: Finds exception based on name and value."""
        if name == 'DivByZero':
            op1, op2 = value
            exc = Except("Division by zero!")
            if op1 == 0 and op2 == 0:
                exc.setReturn('Infinity')
            elif op2 == 0:
                exc.setReturn('undefined')
            return exc
        return Except("No exception", False)

    @classmethod
    def write(cls, dest, src, movecode=0):
        if movecode == 1:
            pc_val = register.load(variable.load("PC"))
            register.store(variable.load("CR"), pc_val)
        elif movecode == 2:
            cr_val = register.load(variable.load("CR"))
            register.store(variable.load("PC"), cr_val)
        elif movecode == 3:
            mi = int(variable.data.get("MI", 0))
            msg_storage = variable.data.get("MSG", {})
            src = msg_storage.get(mi, "")
            variable.data["MI"] = mi + 1

        if isinstance(dest, tuple):
            addr, storage = dest
            storage.store(addr, src)

    @classmethod
    def execute(cls, result, opcode):
        write_bit = int(opcode[1])
        category = opcode[2:]

        if write_bit == 1:
            op1_val, op2_val = result
            if category == "000":
                return op1_val % op2_val
            elif category == "001":
                return op1_val + op2_val
            elif category == "010":
                return op1_val - op2_val
            elif category == "011":
                return op1_val * op2_val
            elif category == "100":
                if op2_val == 0:
                    exc = cls.exception('DivByZero', (op1_val, op2_val))
                    return exc.getReturn()
                return op1_val / op2_val
            return None

        jr_val = register.load(int(variable.load("JR")))
        should_jump = False
        if category == "000":
            should_jump = (jr_val == 0)
        elif category == "001":
            should_jump = (jr_val != 0)
        elif category == "010":
            should_jump = (jr_val < 0)
        elif category == "011":
            should_jump = (jr_val <= 0)
        elif category == "100":
            should_jump = (jr_val > 0)
        elif category == "101":
            should_jump = (jr_val >= 0)
        elif category == "110":
            should_jump = True

        return result if should_jump else None

    @classmethod
    def getOp(cls, inscode):
        if len(inscode) == 16:
            return AddressingMode.immediate(inscode)

        mode = inscode[:3]
        addr_bits = inscode[3:]
        addr_int = int(addr_bits, 2)
        hp_addr = HalfPrecision.hpdec2bin(addr_int)

        if mode == "000":
            return AddressingMode.register(hp_addr)
        elif mode == "001":
            return AddressingMode.register_indirect(hp_addr)
        elif mode == "010":
            return AddressingMode.direct(hp_addr)
        elif mode == "011":
            return AddressingMode.indirect(hp_addr)
        elif mode == "100":
            disp_type = addr_bits[0]
            disp_addr = int(addr_bits[1:], 2)
            disp = register.load(disp_addr) if disp_type == "0" else memory.load(disp_addr)
            return AddressingMode.indexed(disp)
        elif mode == "101":
            sign_bit = addr_bits[0]
            disp = int(addr_bits[1:], 2)
            if sign_bit == "1":
                disp = -disp
            return AddressingMode.indexed(disp)
        elif mode == "110":
            return AddressingMode.autoinc(hp_addr)
        elif mode == "111":
            return AddressingMode.autodec(hp_addr)

        return None

    @classmethod
    def run(cls):
        while True:
            ir_addr = variable.load("IR")
            ir_ptr = int(register.load(ir_addr))
            inscode = memory.load(ir_ptr)
            if not isinstance(inscode, str) or len(inscode) != 32 or inscode == "0"*32:
                break

            opcode = inscode[0:5]
            ib = inscode[5]
            op1_code = inscode[6:16]
            rb = inscode[16]
            op2_code = inscode[17:27]
            extra = inscode[27:32]

            execute_bit = int(opcode[0])
            write_bit = int(opcode[1])
            op1_result = cls.getOp(op1_code)

            if ib == "1":
                hp_immediate = rb + op2_code + extra
                op2_result = cls.getOp(hp_immediate)
            elif rb == "1":
                mode_bits = op2_code[:3]
                addr_bits = op2_code[3:]
                if mode_bits in ("000", "001"):
                    disp_addr = int(addr_bits, 2)
                    disp = register.load(disp_addr) if mode_bits == "000" else memory.load(disp_addr)
                    op2_result = AddressingMode.based(disp)
                elif mode_bits in ("010", "011"):
                    disp = int(addr_bits, 2)
                    if mode_bits == "011":
                        disp = -disp
                    op2_result = AddressingMode.based(disp)
                else:
                    disp = int(addr_bits, 2)
                    if mode_bits in ("011", "111"):
                        disp = -disp
                    op2_result = AddressingMode.relative(disp)
            else:
                op2_result = cls.getOp(op2_code)

            def extract_value(result):
                if result is None:
                    return 0
                return result[1] if isinstance(result, tuple) else result

            def extract_addr(result):
                if result is None:
                    return 0
                return result[0] if isinstance(result, tuple) else result

            if execute_bit == 1 and write_bit == 1:
                val1 = extract_value(op1_result)
                val2 = extract_value(op2_result)
                result = cls.execute((val1, val2), opcode)
                if result is not None:
                    addr1 = int(op1_result[0])
                    storage1 = op1_result[2] if len(op1_result) > 2 else memory
                    cls.write((addr1, storage1), result)
            
            elif execute_bit == 1 and write_bit == 0:
                # Jump operations: JEQ, JNE, JLT, JLE, JGT, JGE, JMP
                # Op1 is the target address
                target_addr = extract_addr(op1_result)
                jump_result = cls.execute(target_addr, opcode)
                
                # If jump_result is not None, update PC to target
                if jump_result is not None:
                    pc_addr = variable.load("PC")
                    register.store(pc_addr, int(jump_result))
            
            elif execute_bit == 0 and write_bit == 1:
                # Move/Write operations: MOV, ADDPC, CALL, RET, SCAN
                val2 = extract_value(op2_result)
                
                # Determine move code
                movecode = 0
                category = opcode[2:]
                if category == "001":  # CALL
                    movecode = 1
                elif category == "010":  # RET
                    movecode = 2
                elif category == "011":  # SCAN
                    movecode = 3
                
                # Get destination from Op1
                if isinstance(op1_result, tuple) and len(op1_result) > 2:
                    addr1, storage1 = op1_result[0], op1_result[2]
                else:
                    addr1, storage1 = op1_result[0] if isinstance(op1_result, tuple) else op1_result, memory
                
                cls.write((int(addr1), storage1), val2, movecode)
            
            elif execute_bit == 0 and write_bit == 0:
                # Print operations: PRNT, EOP, FUNC
                val1 = extract_value(op1_result)
                print(val1)
            
            # Update PC for next instruction
            pc_addr = variable.load("PC")
            current_pc = int(register.load(pc_addr))
            ir_addr = variable.load("IR")
            
            # Move PC to IR, then increment PC
            register.store(ir_addr, current_pc)
            register.store(pc_addr, current_pc + 1)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'r') as f:
            prog_lines = f.readlines()
        p = Program(prog_lines)
        p.run()
