# =============================================================
#  addressing.py
#  Johann's part — Access.store() + full AddressingMode class
# =============================================================
#
#  Quick memory map reminder (from storage.py):
#  Register slots:  1-8  = R1-R8 (general purpose)
#                   9    = BR  (Base Register)
#                   10   = XR  (Index Register)
#                   11   = ACC (Accumulator)
#                   12   = IR  (Instruction Register)
#                   13   = PC  (Program Counter)
#                   14   = JR  (Jump Register)
#                   15   = CR  (Call Register)
#  Memory slots:    1-8  = Variables A-H
#                   9-56 = Instructions
#                   57-64= Blocks B1-B8
#                   65-68= Function Blocks F1-F4
# =============================================================

from bin_convert import HalfPrecision, Length
from storage import memory, register, variable


# ─────────────────────────────────────────────────────────────
#  Access
#  A helper class that makes reading/writing storage easier.
# ─────────────────────────────────────────────────────────────
class Access:

    # ── GIVEN (provided by the instructor – do NOT modify) ───
    @staticmethod
    def data(addr, flow):
        """
        Follows a 'flow' of storages to load a final value.

        How it works (step by step):
          - Start with 'addr' as the initial key/address.
          - For each storage name in 'flow', load from that
            storage using the current result as the address.
          - Return whatever the last load gives you.

        Example: data('PC', ['var', 'reg'])
          Step 1 → variable.load('PC')  = 13   (register slot of PC)
          Step 2 → register.load(13)    = 10   (actual PC value)
          Returns 10

        Parameters:
            addr  – starting key (a name like 'PC', or an integer)
            flow  – list of storage names: 'var', 'reg', or 'mem'
        """
        storage_map = {
            'var': variable,
            'reg': register,
            'mem': memory
        }
        result = addr
        for storage_name in flow:
            result = storage_map[storage_name].load(result)
        return result
    # ── END GIVEN ─────────────────────────────────────────────

    @staticmethod
    def store(typ, addr, value):
        """
        Stores a value into the register OR memory.

        Think of it like saving a number to a specific slot:
          - 'reg' → saves into the register storage
          - 'mem' → saves into the memory storage

        Parameters:
            typ   – 'reg' for register, 'mem' for memory
            addr  – the slot number (integer) where value goes
            value – the value to store (number or binary string)
        """
        if typ == 'reg':
            register.store(addr, value)
        elif typ == 'mem':
            memory.store(addr, value)


# ─────────────────────────────────────────────────────────────
#  AddressingMode
#  Each static method is a different strategy for finding
#  the data an instruction is referring to.
#
#  A quick visual guide to all modes:
#
#  Immediate        → the value IS the operand (no lookup)
#  Register         → value is inside a register
#  Register Indirect→ register holds a MEMORY address → go there
#  Direct           → memory address given directly → go there
#  Indirect         → memory[addr] holds ANOTHER address → go there
#  Indexed          → XR + displacement → memory address
#  Auto-Increment   → like register indirect, then reg += 1
#  Auto-Decrement   → reg -= 1, then like register indirect
#  Relative         → PC + displacement → effective address
#  Based            → BR + displacement → effective address
# ─────────────────────────────────────────────────────────────
class AddressingMode:

    # ----------------------------------------------------------
    @staticmethod
    def immediate(var):
        """
        Immediate Addressing Mode.

        The operand is the value itself — no memory lookup needed.
        It is stored in Half Precision (HP) binary format, so we
        just convert it back to a decimal number.

        Example instruction: ADD R1, 5
          → '5' is encoded as HP binary and passed as 'var'
          → we decode it and return 5.0

        Parameters:
            var – a Half Precision binary string (16 bits)

        Returns: the decimal value of var
        Note: always used as the SECOND operand only.
        """
        # HP binary string → decimal number
        return HalfPrecision.hpbin2dec(var)

    # ----------------------------------------------------------
    @staticmethod
    def relative(displace):
        """
        Relative Addressing Mode.

        Effective address = current Program Counter (PC) + displacement.
        Returns the value at that address.

        Parameters:
            displace – an integer offset (positive = forward, negative = backward)

        Returns: the value stored in memory at (PC + displace)
        Note: always used as the SECOND operand only.
        """
        # Retrieve the current value of PC from the register
        pc_value = Access.data('PC', ['var', 'reg'])

        return memory.load(int(pc_value + displace))

    # ----------------------------------------------------------
    @staticmethod
    def based(displace):
        """
        Based Addressing Mode.

        Effective address = Base Register (BR) value + displacement.
        Returns the value at that address.

        Parameters:
            displace – an integer offset

        Returns: the value stored in memory at (BR + displace)
        Note: always used as the SECOND operand only.
        """
        # Retrieve the current value of BR from the register
        br_value = Access.data('BR', ['var', 'reg'])

        return memory.load(int(br_value + displace))

    # ----------------------------------------------------------
    @staticmethod
    def indexed(displace):
        """
        Indexed Addressing Mode.

        Effective address = Index Register (XR) value + displacement.
        Then we look up MEMORY at that effective address to get the value.

        Useful for looping through arrays:
          XR acts as a pointer, displacement shifts it.

        Parameters:
            displace – an integer offset (can be negative)

        Returns: (effective_addr, value)
            effective_addr – the computed memory address (XR + displace)
            value          – what is stored in memory at that address
        """
        # Get the current value of XR (Index Register)
        # Flow: variable['XR'] → register address of XR (10)
        #        register[10]  → current XR value
        xr_value = Access.data('XR', ['var', 'reg'])

        # Compute the target memory address
        effective_addr = xr_value + displace

        # Read the value from memory at that address
        value = memory.load(int(effective_addr))

        return effective_addr, value

    # ----------------------------------------------------------
    @staticmethod
    def register(reg_addr):
        """
        Register Addressing Mode.

        The operand is the value stored directly inside a register.

        Parameters:
            reg_addr – a Half Precision binary string encoding
                       the register slot number (e.g. HP of 1 → R1)

        Returns: (effective_addr, value, register)
            effective_addr – the register slot number (decimal)
            value          – the value stored in that register slot
            register       – the register Storage object itself
                             (returned so the caller knows it's a register,
                              not memory — important for write-back)
        """
        # Decode the HP binary → actual register slot number
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)

        # Read what is stored in that register slot
        value = register.load(int(effective_addr))

        # Return the storage object too (unique to register mode)
        return effective_addr, value, register

    # ----------------------------------------------------------
    @staticmethod
    def register_indirect(reg_addr):
        """
        Register Indirect Addressing Mode.

        The register does NOT hold the final value — it holds a
        MEMORY ADDRESS. We have to follow it to get the real value.

        Diagram:  reg[reg_addr]  →  mem_addr  →  value
                      (register)       (memory)

        Parameters:
            reg_addr – HP binary string for the register slot number

        Returns: (effective_addr, value)
            effective_addr – the register slot number
            value          – the value found in memory
        """
        # Step 1: Decode HP binary → register slot number
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)

        # Step 2: The register contains a memory address — load it
        mem_addr = register.load(int(effective_addr))

        # Step 3: Use that memory address to get the actual value
        value = memory.load(int(mem_addr))

        return effective_addr, value

    # ----------------------------------------------------------
    @staticmethod
    def direct(var_addr):
        """
        Direct Addressing Mode.

        The instruction gives us a memory address directly.
        We just go straight to that memory slot to get the value.

        Diagram:  var_addr  →  memory[var_addr]  →  value

        Parameters:
            var_addr – HP binary string encoding the memory address

        Returns: (effective_addr, value)
            effective_addr – the memory slot number (decimal)
            value          – the value stored at that memory slot
        """
        # Decode HP binary → actual memory slot number
        effective_addr = HalfPrecision.hpbin2dec(var_addr)

        # Read the value directly from memory
        value = memory.load(int(effective_addr))

        return effective_addr, value

    # ----------------------------------------------------------
    @staticmethod
    def indirect(var_addr):
        """
        Indirect Addressing Mode.

        Double indirection: the memory address given holds
        ANOTHER memory address, and the real value is there.

        Diagram:  var_addr  →  memory[var_addr]  →  second_addr
                                                 →  memory[second_addr]  →  value

        Parameters:
            var_addr – HP binary string for the FIRST memory address

        Returns: (effective_addr, value)
            effective_addr – the first memory slot number
            value          – the value found at the second memory address
        """
        # Step 1: Decode HP binary → first memory address
        effective_addr = HalfPrecision.hpbin2dec(var_addr)

        # Step 2: Memory at that address holds a SECOND address
        second_addr = memory.load(int(effective_addr))

        # Step 3: Follow the second address to get the real value
        value = memory.load(int(second_addr))

        return effective_addr, value

    # ----------------------------------------------------------
    @staticmethod
    def autoinc(reg_addr):
        """
        Auto-Increment Addressing Mode.

        Works like Register Indirect — access memory through the
        register — but AFTER the access, the register value goes up by 1.

        Useful for stepping forward through an array automatically.

        Order of operations:
          1. Get the memory address from the register
          2. Read the value from memory  ← this is the result
          3. Increment the register by 1

        Parameters:
            reg_addr – HP binary string for the register slot number

        Returns: (effective_addr, value)
            effective_addr – the register slot number
            value          – the value read from memory (BEFORE increment)
        """
        # Decode HP binary → register slot number
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)

        # Register holds a memory address → read the value there
        mem_addr = register.load(int(effective_addr))
        value = memory.load(int(mem_addr))

        # AFTER reading, increment the register by 1
        register.store(int(effective_addr), mem_addr + 1)

        return effective_addr, value

    # ----------------------------------------------------------
    @staticmethod
    def autodec(reg_addr):
        """
        Auto-Decrement Addressing Mode.

        Like Auto-Increment but in reverse — the register goes DOWN
        by 1 BEFORE the memory access happens.

        Useful for stepping backward through an array (like a stack pop).

        Order of operations:
          1. Decrement the register by 1
          2. Get the (now lower) memory address from the register
          3. Read the value from memory  ← this is the result

        Parameters:
            reg_addr – HP binary string for the register slot number

        Returns: (effective_addr, value)
            effective_addr – the register slot number
            value          – the value read from memory (AFTER decrement)
        """
        # Decode HP binary → register slot number
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)

        # Get current memory address from register, then decrement it
        mem_addr = register.load(int(effective_addr))
        register.store(int(effective_addr), mem_addr - 1)

        # Re-read the updated (decremented) memory address
        new_mem_addr = register.load(int(effective_addr))

        # Read the value from memory at the new (lower) address
        value = memory.load(int(new_mem_addr))

        return effective_addr, value
