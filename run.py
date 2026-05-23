from bin_convert import HalfPrecision, Length
from storage import memory, register, variable
from addressing import Access, AddressingMode
from compiler import Instruction

class Except(Exception):
    def __init__(self, msg, occur=True):
        self.message = msg
        self.occur = occur
        self.ret = None

    @classmethod
    def dispMSG(cls, self): # Signature might be weird if called as class method on instance
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
        """Requirement VI.3: Perform Write operations."""
        # movecode logic
        if movecode == 1: # CALL
            pc_val = register.load(variable.load("PC"))
            register.store(variable.load("CR"), pc_val)
        elif movecode == 2: # RET
            cr_val = register.load(variable.load("CR"))
            register.store(variable.load("PC"), cr_val)
        elif movecode == 3: # SCAN
            # In a real system we'd ask user, here we might have a message/value
            # Prompt says "change the src by the value of the message"
            pass
        
        # Default move: src to dest
        # dest can be (address, storage_object) or just address if we assume storage
        if isinstance(dest, tuple):
            addr, storage = dest
            storage.store(addr, src)
        else:
            # Fallback if dest is just an address, assume register for now or handled elsewhere
            pass

    @classmethod
    def execute(cls, result, opcode):
        """Requirement VI.4: Perform Execute operations."""
        write_bit = int(opcode[1])
        category = opcode[2:]
        
        if write_bit == 1:
            # Perform four basic operations and modulo
            # Categories: 000 MOD, 001 ADD, 010 SUB, 011 MUL, 100 DIV
            # Category 001 is also shared by CB/CF but they simplify to ADD
            op1_val, op2_val = result
            if category == "000": return op1_val % op2_val
            if category == "001": return op1_val + op2_val
            if category == "010": return op1_val - op2_val
            if category == "011": return op1_val * op2_val
            if category == "100": # DIV
                if op2_val == 0:
                    exc = cls.exception('DivByZero', (op1_val, op2_val))
                    return exc.getReturn()
                return op1_val / op2_val
        else:
            # Perform jumps based on category
            # Categories: 000 JEQ, 001 JNE, 010 JLT, 011 JLE, 100 JGT, 101 JGE, 110 JMP
            jr_val = register.load(variable.load("JR"))
            target_pc = result # In jumps, result is typically the target address from op1
            
            should_jump = False
            if category == "000": should_jump = (jr_val == 0)
            elif category == "001": should_jump = (jr_val != 0)
            elif category == "010": should_jump = (jr_val < 0)
            elif category == "011": should_jump = (jr_val <= 0)
            elif category == "100": should_jump = (jr_val > 0)
            elif category == "101": should_jump = (jr_val >= 0)
            elif category == "110": should_jump = True
            
            if should_jump:
                register.store(variable.load("PC"), target_pc)
        return None

    @classmethod
    def getOp(cls, inscode):
        """Requirement VI.5: Gets effective address and storage type."""
        # inscode is 10 bits or 16 bits if immediate
        if len(inscode) == 16:
            # alpha: immediate
            return AddressingMode.immediate(inscode)
        
        mode = inscode[:3]
        addr_bits = inscode[3:]
        hp_addr = HalfPrecision.hpdec2bin(int(addr_bits, 2))
        
        # Identify based, indexed, or relative for displacement
        if mode in ("000", "001", "010", "011") and False: # Placeholder for rb/ib logic
            pass
            
        # Call appropriate addressing mode
        # Mapping from IV.3/IV.6
        if mode == "000": return AddressingMode.register(hp_addr)
        if mode == "001": return AddressingMode.register_indirect(hp_addr)
        if mode == "010": return AddressingMode.direct(hp_addr)
        if mode == "011": return AddressingMode.indirect(hp_addr)
        if mode == "100": # Indexed (register/memory displacement)
            # addr_bits[0] is displacement type
            disp = int(addr_bits[1:], 2)
            return AddressingMode.indexed(disp)
        if mode == "101": # Indexed (integer displacement)
            # addr_bits[0] is sign
            sign = -1 if addr_bits[0] == "1" else 1
            disp = sign * int(addr_bits[1:], 2)
            return AddressingMode.indexed(disp)
        if mode == "110": return AddressingMode.autoinc(hp_addr)
        if mode == "111": return AddressingMode.autodec(hp_addr)
        
        return None

    @classmethod
    def run(cls):
        """Requirement VI.6: Execute Instruction Codes starting from address in IR."""
        # Initialize monadic/niladic (empty for now)
        monadic = []
        niladic = []
        
        while True:
            # Gets value of IR (current instruction pointer)
            ir_ptr = int(register.load(variable.load("IR")))
            inscode = memory.load(ir_ptr)
            
            # Break if not 32-bit or all zeros
            if not isinstance(inscode, str) or len(inscode) != 32 or inscode == "0"*32:
                break
            
            # Slice bits
            opcode = inscode[0:5]
            ib = inscode[5]
            op1_code = inscode[6:16]
            rb = inscode[16]
            op2_code = inscode[17:27]
            extra = inscode[27:32]
            
            execute_bit = int(opcode[0])
            write_bit = int(opcode[1])
            
            # Get Operands
            # Op1 is always 10 bits
            op1_res = cls.getOp(op1_code)
            
            # Op2 depends on ib/rb
            if ib == "1":
                # Immediate mode: bits 16 (rb) + 17-31 (op2_code + extra) = 16 bits
                op2_res = cls.getOp(rb + op2_code + extra)
            elif rb == "1":
                # Relative/Based: use AddressingMode directly or via getOp with context
                # Since getOp signature is just inscode, we might need to adjust
                # Prompt III.13 says they return value only.
                # If rb=1, Op2Mode(3) + Op2Addr(7) are relative/based
                sign = -1 if op2_code[3] == "1" else 1
                disp = sign * int(op2_code[4:], 2)
                mode_type = op2_code[:3]
                if mode_type.startswith("1"): # Relative
                    op2_res = AddressingMode.relative(disp)
                else: # Based
                    op2_res = AddressingMode.based(disp)
            else:
                op2_res = cls.getOp(op2_code)

            # Execute & Write
            if execute_bit == 1:
                # dyadic operations need two values
                # op1_res can be (addr, val, storage) or (addr, val)
                val1 = op1_res[1] if isinstance(op1_res, tuple) else op1_res
                val2 = op2_res[1] if isinstance(op2_res, tuple) else op2_res
                
                exec_res = cls.execute((val1, val2), opcode)
                
                if write_bit == 1:
                    # Target is typically op1
                    dest = (int(op1_res[0]), op1_res[2] if len(op1_res) > 2 else memory)
                    cls.write(dest, exec_res)
            
            elif write_bit == 1:
                # E.g. MOV, ADDPC, CALL, RET, SCAN (Execute Bit 0, Write Bit 1)
                movecode = 0
                category = opcode[2:]
                if category == "001": movecode = 1 # CALL
                elif category == "010": movecode = 2 # RET
                elif category == "011": movecode = 3 # SCAN
                
                val2 = op2_res[1] if isinstance(op2_res, tuple) else op2_res
                dest = (int(op1_res[0]), op1_res[2] if len(op1_res) > 2 else memory)
                cls.write(dest, val2, movecode)
            
            elif execute_bit == 0 and write_bit == 0:
                # PRNT - typically prints Op1 if it's a single-operand call like 'PRNT R1'
                val1 = op1_res[1] if isinstance(op1_res, tuple) else op1_res
                print(val1)

            # Move PC to IR, then increment PC
            # The prompt says: "Move the value of 'PC' to 'IR', then increment the value of 'PC' by 1."
            pc_val = int(register.load(variable.load("PC")))
            register.store(variable.load("IR"), pc_val)
            register.store(variable.load("PC"), pc_val + 1)

if __name__ == "__main__":
    import sys
    # Requirement VII.7: Running from file
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'r') as f:
            prog_lines = f.readlines()
        p = Program(prog_lines)
        p.run()
