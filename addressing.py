from bin_convert import HalfPrecision, Length
from storage import memory, register, variable

class Access:
    @staticmethod
    def data(addr, flow):
        storage_map = {'var': variable, 'reg': register, 'mem': memory}
        result = addr
        for storage_name in flow:
            result = storage_map[storage_name].load(result)
        return result

    @staticmethod
    def store(typ, addr, value):
        if typ == 'reg':
            register.store(addr, value)
        elif typ == 'mem':
            memory.store(addr, value)


class AddressingMode:
    @staticmethod
    def immediate(var):
        return HalfPrecision.hpbin2dec(var)

    @staticmethod
    def relative(displace):
        pc_value = Access.data('PC', ['var', 'reg'])
        return memory.load(int(pc_value + displace))

    @staticmethod
    def based(displace):
        br_value = Access.data('BR', ['var', 'reg'])
        return memory.load(int(br_value + displace))

    @staticmethod
    def indexed(displace):
        xr_value = Access.data('XR', ['var', 'reg'])
        effective_addr = xr_value + displace
        value = memory.load(int(effective_addr))
        return effective_addr, value

    @staticmethod
    def register(reg_addr):
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)
        value = register.load(int(effective_addr))
        return effective_addr, value, register

    @staticmethod
    def register_indirect(reg_addr):
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)
        mem_addr = register.load(int(effective_addr))
        value = memory.load(int(mem_addr))
        return effective_addr, value

    @staticmethod
    def direct(var_addr):
        effective_addr = HalfPrecision.hpbin2dec(var_addr)
        value = memory.load(int(effective_addr))
        return effective_addr, value

    @staticmethod
    def indirect(var_addr):
        effective_addr = HalfPrecision.hpbin2dec(var_addr)
        second_addr = memory.load(int(effective_addr))
        value = memory.load(int(second_addr))
        return effective_addr, value

    @staticmethod
    def autoinc(reg_addr):
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)
        mem_addr = register.load(int(effective_addr))
        value = memory.load(int(mem_addr))
        register.store(int(effective_addr), mem_addr + 1)
        return effective_addr, value

    @staticmethod
    def autodec(reg_addr):
        effective_addr = HalfPrecision.hpbin2dec(reg_addr)
        mem_addr = register.load(int(effective_addr))
        register.store(int(effective_addr), mem_addr - 1)
        new_mem_addr = register.load(int(effective_addr))
        value = memory.load(int(new_mem_addr))
        return effective_addr, value
