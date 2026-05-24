# Design Documentation

## Overview

This repository implements a simple ISA emulator for the CMSC132 project. The system is structured into a compiler/encoder, a runtime program executor, storage abstractions, and addressing mode helpers.

## What was implemented

### Core components
- `run.py`
  - `Program` class that loads instruction bitstrings into memory, fetches and decodes instructions, executes them, and updates the program counter.
  - `Except` class for runtime exception reporting.
  - `Program.encode_program()` supports block instructions (`CB` and `CF`) and writes an ordered instruction stream into memory.
  - `Program.execute()` handles opcode dispatch for arithmetic, branches, `CALL`, `RET`, `SCAN`, `PRNT`, and halt semantics.

- `compiler.py`
  - `Instruction` parser for 32-bit instruction words.
  - Instruction encoding helpers: `encodeOp()`, `resolve_address()`, and `encode()`.
  - Opcode tables and mapping from `(execute, write, category)` bits to instruction names.
  - Support for immediate operands using half-precision floating-point format.
  - `FUNC` encoding support as a no-operand instruction.

- `addressing.py`
  - `Access` helper for layered data flows across variables, registers, and memory.
  - `AddressingMode` class with register, indirect, direct, indexed, auto-increment, and auto-decrement modes.

- `storage.py`
  - Simulated storage for memory, registers, and variables.
  - Half-precision-aware load/store behavior for values stored as binary strings.
  - Initialization of register and memory layout, including special registers: `BR`, `XR`, `ACC`, `IR`, `PC`, `JR`, `CR`.

- `bin_convert.py`
  - Half-precision binary conversion utilities for immediate values and address encoding.

- `test_run.py`
  - Comprehensive coverage for arithmetic operations, `PRNT`, branching, and addressing modes.
  - Verifies encoding of ISA opcodes and runtime correctness.

## How it was implemented

### Instruction encoding
- Each instruction is represented as a 32-bit binary string.
- `Instruction.encodeOp()` maps human-readable opcodes to the two execute/write bits plus a 3-bit category code.
- Operands can be registers or immediate values.
- Immediate values are converted with `HalfPrecision.hpdec2bin()` and placed into the instruction format.
- `FUNC` is encoded as a valid instruction with no operands, while `EOP` is encoded as an all-zero word.

### Runtime execution
- `Program.run()` repeatedly calls `step()` until halted or the step limit is reached.
- `step()` fetches the raw instruction from memory, decodes it, and executes it.
- `execute()` handles opcode-specific semantics and returns whether the PC was changed explicitly.
- `PRNT` prints the selected operand value.
- Branches read the jump register (`JR`) and update `PC` accordingly.
- `CALL` and `RET` use call-register semantics inside `write()` and `write_pc()` logic.

### Block handling
- `Program.encode_program()` supports `CB` and `CF` by placing block instructions at the front of the instruction list.
- Block addresses are stored in the corresponding block registers and the block count is stored in `BR`.
- This preserves the block resolution semantics required by the ISA.

### Addressing modes
- `AddressingMode` implements the supported addressing modes with `Access` and `Storage`.
- This makes it possible to fetch values from registers, memory, or computed addresses consistently.
- Auto-increment and auto-decrement update the index register after or before memory access.

## Why this design

- Separation of concerns
  - Compiler/encoder logic is kept separate from runtime execution.
  - Storage and addressing logic are abstracted so instruction execution can stay focused on semantics.

- Ease of validation
  - `test_run.py` is designed to validate both encoded instruction generation and runtime behavior.
  - The test suite covers arithmetic, branches, and multiple memory addressing modes.

- ISA alignment
  - The implementation follows the course ISA by using 32-bit instructions, opcode bit groupings, immediate operand encoding, and special registers like `BR`, `PC`, and `JR`.

## Notes and future work

- The current implementation supports a broad set of ISA features, but extended `CALL`/`RET` stack and parameter handling can still be improved.
- Additional tests can be added for `SCAN`, `FUNC`, and explicit block semantics.
- `README.md` contains usage commands and a summary of supported functionality.
