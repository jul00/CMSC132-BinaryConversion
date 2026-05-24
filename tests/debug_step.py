from run import Program, register, variable, memory
from compiler import Instruction

p = Program(['MOV R1 5', 'PRNT R1', 'EOP'], start_address=10)
print('mem[10]:', Instruction(memory.load(10)).mnemonic, Instruction(memory.load(10)).op1_addr)
print('mem[11]:', Instruction(memory.load(11)).mnemonic, Instruction(memory.load(11)).op1_addr)

for step_num in range(3):
    pc_val = int(p.read_pc())
    raw = memory.load(pc_val)
    r1 = register.load(1)
    print(f'Step {step_num}: PC={pc_val}, R1 before={r1}, raw len={len(raw)}')
    decoded = Instruction(raw)
    print(f'  decoded={decoded.mnemonic}')
    p.step()
    r1_after = register.load(1)
    print(f'  R1 after step={r1_after}')
