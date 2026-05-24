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
        """Requirement VI.3: Perform Write operations."""
        # movecode logic
        if movecode == 1: # CALL
            pc_val = register.load(variable.load("PC"))
            register.store(variable.load("CR"), pc_val)
        elif movecode == 2: # RET
            cr_val = register.load(variable.load("CR"))
            register.store(variable.load("PC"), cr_val)
        elif movecode == 3: # SCAN
            mi = int(variable.data.get("MI", 0))
            msg_storage = variable.data.get("MSG", {})
            src = msg_storage.get(mi, "")
            variable.data["MI"] = mi + 1
        
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
            # Dyadic operations with write: MOD, ADD, SUB, MUL, DIV, CMP
            # result is a tuple (op1_val, op2_val)
            op1_val, op2_val = result
            
            if category == "000":  # MOD
                return op1_val % op2_val
            elif category == "001":  # ADD
                return op1_val + op2_val
            elif category == "010":  # SUB
                return op1_val - op2_val
            elif category == "011":  # MUL
                return op1_val * op2_val
            elif category == "100":  # DIV
                if op2_val == 0:
                    exc = cls.exception('DivByZero', (op1_val, op2_val))
                    return exc.getReturn()
                return op1_val / op2_val
            else:
                return None
        else:
            # Jump operations: JEQ, JNE, JLT, JLE, JGT, JGE, JMP
            # result is the target address (op1 effective address)
            # We need to check the jump condition based on JR value
            jr_val = register.load(int(variable.load("JR")))
            
            should_jump = False
            if category == "000":  # JEQ: Jump if JR == 0
                should_jump = (jr_val == 0)
            elif category == "001":  # JNE: Jump if JR != 0
                should_jump = (jr_val != 0)
            elif category == "010":  # JLT: Jump if JR < 0
                should_jump = (jr_val < 0)
            elif category == "011":  # JLE: Jump if JR <= 0
                should_jump = (jr_val <= 0)
            elif category == "100":  # JGT: Jump if JR > 0
                should_jump = (jr_val > 0)
            elif category == "101":  # JGE: Jump if JR >= 0
                should_jump = (jr_val >= 0)
            elif category == "110":  # JMP: Unconditional jump
                should_jump = True
            
            if should_jump:
                # Return the target address to be set as new PC
                return result
            else:
                # Don't jump; return None or current PC
                return None

    @classmethod
    def getOp(cls, inscode):
        """Requirement VI.5: Gets effective address and storage type."""
        # inscode is 10 bits or 16 bits if immediate
        if len(inscode) == 16:
            # alpha: immediate - return the decoded value directly
            return AddressingMode.immediate(inscode)
        
        # Standard 10-bit operand code: Mode(3) + Addr(7)
        mode = inscode[:3]
        addr_bits = inscode[3:]
        addr_int = int(addr_bits, 2)
        
        # Convert address to Half Precision binary format for addressing mode methods
        hp_addr = HalfPrecision.hpdec2bin(addr_int)
        
        # Call appropriate addressing mode based on mode bits
        if mode == "000":  # Register addressing
            return AddressingMode.register(hp_addr)
        elif mode == "001":  # Register indirect
            return AddressingMode.register_indirect(hp_addr)
        elif mode == "010":  # Direct addressing
            return AddressingMode.direct(hp_addr)
        elif mode == "011":  # Indirect addressing
            return AddressingMode.indirect(hp_addr)
        elif mode == "100":  # Indexed with register/memory displacement
            # First bit: 0=register displacement, 1=memory displacement
            # Remaining 6 bits: displacement address
            disp_type = addr_bits[0]
            disp_addr = int(addr_bits[1:], 2)
            if disp_type == "0":  # Register displacement
                disp = register.load(disp_addr)
            else:  # Memory displacement
                disp = memory.load(disp_addr)
            return AddressingMode.indexed(disp)
        elif mode == "101":  # Indexed with integer displacement
            # First bit: 0=positive, 1=negative
            sign_bit = addr_bits[0]
            disp_val = int(addr_bits[1:], 2)
            disp = disp_val if sign_bit == "0" else -disp_val
            return AddressingMode.indexed(disp)
        elif mode == "110":  # Auto-increment
            return AddressingMode.autoinc(hp_addr)
        elif mode == "111":  # Auto-decrement
            return AddressingMode.autodec(hp_addr)
        
        return None

    @classmethod
    def run(cls):
        """Requirement VI.6: Execute Instruction Codes starting from address in IR."""
        
        while True:
            # Gets value of IR (current instruction register)
            ir_addr = variable.load("IR")
            ir_ptr = int(register.load(ir_addr))
            inscode = memory.load(ir_ptr)
            
            # Break if not 32-bit or all zeros (end of program)
            if not isinstance(inscode, str) or len(inscode) != 32 or inscode == "0"*32:
                break
            
            # Parse instruction bits
            opcode = inscode[0:5]        # 5 bits: opcode
            ib = inscode[5]              # 1 bit: immediate flag for Op2
            op1_code = inscode[6:16]     # 10 bits: Op1 addressing mode + address
            rb = inscode[16]             # 1 bit: relative/based flag (or HP sign if ib=1)
            op2_code = inscode[17:27]    # 10 bits: Op2 addressing mode + address
            extra = inscode[27:32]       # 5 bits: extra bits for immediate
            
            execute_bit = int(opcode[0])
            write_bit = int(opcode[1])
            
            # Get Operand 1 (always 10-bit addressing mode code)
            op1_result = cls.getOp(op1_code)
            
            # Get Operand 2 (depends on ib/rb flags)
            if ib == "1":
                # Immediate addressing: combine rb + op2_code + extra into 16-bit HP
                hp_immediate = rb + op2_code + extra
                op2_result = cls.getOp(hp_immediate)
            elif rb == "1":
                # Relative or Based addressing mode
                mode_bits = op2_code[:3]
                addr_bits = op2_code[3:]
                
                # Decode displacement based on mode
                if mode_bits == "000" or mode_bits == "001":  # Based addressing
                    # Mode 000: displacement from register
                    # Mode 001: displacement from memory
                    if mode_bits == "000":
                        disp_addr = int(addr_bits, 2)
                        disp = register.load(disp_addr)
                    else:
                        disp_addr = int(addr_bits, 2)
                        disp = memory.load(disp_addr)
                    op2_result = AddressingMode.based(disp)
                
                else:  # Relative addressing (modes 100-111 in spec)
                    # Mode 100: positive integer displacement
                    # Mode 101: negative integer displacement
                    disp = int(addr_bits, 2)
                    if mode_bits in ("011", "111"):
                        disp = -disp
                    op2_result = AddressingMode.relative(disp)
            else:
                # Normal addressing mode
                op2_result = cls.getOp(op2_code)
            
            # Extract values from results (handle both tuple and scalar returns)
            def extract_value(result):
                """Extract value from addressing mode result."""
                if result is None:
                    return 0
                elif isinstance(result, tuple):
                    return result[1]  # Return the value component
                else:
                    return result  # Return scalar value directly
            
            def extract_addr(result):
                """Extract effective address from addressing mode result."""
                if result is None:
                    return 0
                elif isinstance(result, tuple):
                    return result[0]  # Return the address component
                else:
                    return result  # Return as address if scalar
            
            # Execute based on instruction type
            if execute_bit == 1 and write_bit == 1:
                # Dyadic operations: ADD, SUB, MUL, DIV, MOD, CMP, CB, CF
                val1 = extract_value(op1_result)
                val2 = extract_value(op2_result)
                result = cls.execute((val1, val2), opcode)
                
                # Write result back to Op1 destination
                if result is not None:
                    addr1, storage1 = op1_result[0], op1_result[2] if len(op1_result) > 2 else memory
                    cls.write((int(addr1), storage1), result)
            
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
    # Requirement VII.7: Running from file
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'r') as f:
            prog_lines = f.readlines()
        p = Program(prog_lines)
        p.run()
