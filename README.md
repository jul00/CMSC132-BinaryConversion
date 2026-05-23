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

```bash
python -c "from run import Program; Program(['MOV R1 5','PRNT R1','EOP']).run()"
```

Project notes
-------------

- `Program` encodes source-style instruction strings, loads them into memory, and executes them from `PC`.
- `test_run.py` contains coverage for arithmetic, memory addressing, and opcode encoding.
- If you add new instructions, update both `compiler.py` and `run.py`.
