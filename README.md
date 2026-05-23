CMSC132 Binary Conversion ISA Emulator
=====================================

This repository implements a small ISA emulator for the CMSC132 course.
It includes:

- `run.py`: runtime `Program` class and instruction execution
- `compiler.py`: instruction encoding/decoding for the 32-bit ISA
- `addressing.py`: addressing mode helpers and memory/register access
- `storage.py`: simulated register/memory/storage model
- `bin_convert.py`: half-precision conversions used by immediates
- `test_run.py`: executable test suite covering core opcodes and addressing modes

Supported features
------------------

- Arithmetic: `MOV`, `ADD`, `SUB`, `MUL`, `DIV`
- Branches: `JMP`, `JEQ`, `JNE`, `JLT`, `JLE`, `JGT`, `JGE`
- Control: `PRNT`, `EOP`, `FUNC`
- Blocks: `CB` / `CF` block encoding support
- Addressing modes: direct, indirect, register indirect, auto-increment, auto-decrement

Usage
-----

Run the project tests:

```bash
python -m py_compile compiler.py run.py test_run.py
python test_run.py
```

Run a quick custom program:

ex. 1 - Simple arithmetic + PRNT
```bash
python -c "from run import Program; Program(['MOV R1 5','ADD R1 7','MUL R1 2','PRNT R1','EOP']).run()"
```
Expected output: 24.0

ex. 2 - Division
```bash
python -c "from run import Program; Program(['MOV R1 20','DIV R1 4','PRNT R1','EOP']).run()"
```
Expected output: 5.0

ex. 3 - Branch Taken
```bash
python -c "from run import Program; Program(['MOV R1 99','MOV JR 1','MOV R4 15','JGT R4','MOV R1 0','PRNT R1','EOP']).run()"
```
Expected output: 99.0

ex. 4 - Branch not Taken
```bash
python -c "from run import Program; Program(['MOV R1 5','MOV JR 0','MOV R4 15','JEQ R4','MOV R1 42','PRNT R1','EOP']).run()"
```
Expected output: 5.0

ex. 5 - PRNT on a different register
```bash
python -c "from run import Program; Program(['MOV R2 7','PRNT R2','EOP']).run()"
```
Expected output: 7.0

ex. 6 - Combine arithmetic and branch
```bash
python -c "from run import Program; Program(['MOV R1 10','MOV R2 2','DIV R1 2','MOV JR 1','MOV R4 15','JGT R4','MOV R1 0','PRNT R1','EOP']).run()"
```
Expected output: 5.0

Project notes
-------------

- `Program` encodes source-style instruction strings, loads them into memory, and executes them from `PC`.
- `test_run.py` contains coverage for arithmetic, memory addressing, and opcode encoding.
- If you add new instructions, update both `compiler.py` and `run.py`.
