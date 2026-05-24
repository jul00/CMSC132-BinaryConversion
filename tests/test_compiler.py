from compiler import Instruction
from storage import register, variable

# Test CALL simplification
try:
    result = Instruction.encode("CALL B1")
    print(f"CALL result type: {type(result)}, value: {result}")
except Exception as e:
    print(f"CALL error: {e}")

# Test CMP simplification  
try:
    result = Instruction.encode("CMP R1")
    print(f"CMP result type: {type(result)}, value: {result}")
except Exception as e:
    print(f"CMP error: {e}")

# Test CB simplification
try:
    result = Instruction.encode("CB B1")
    print(f"CB result type: {type(result)}, value: {result}")
except Exception as e:
    print(f"CB error: {e}")

# Test RET 
try:
    result = Instruction.encode("RET ACC")
    print(f"RET result type: {type(result)}, value: {result}")
except Exception as e:
    print(f"RET error: {e}")

# Test ADDPC
try:
    result = Instruction.encode("ADDPC R1 5")
    print(f"ADDPC result type: {type(result)}, value: {result}")
except Exception as e:
    print(f"ADDPC error: {e}")
