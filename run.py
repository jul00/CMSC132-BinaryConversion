# =============================================================
#  run.py
#  Johann's part  → Except class  (top of the file)
#  Julo's part    → Program class (will be added below)
# =============================================================

from bin_convert import HalfPrecision, Length
from storage import memory, register, variable
from addressing import Access, AddressingMode
from compiler import Instruction


# ─────────────────────────────────────────────────────────────
#  Except
#  A simple container that describes an exception (error)
#  that can happen during program execution.
#
#  Think of it like a custom error report card:
#    - What went wrong? (message)
#    - Did it actually happen? (occur)
#    - What should be returned instead? (ret)
# ─────────────────────────────────────────────────────────────
class Except:

    def __init__(self, msg, occur=True):
        """
        Create a new exception.

        Parameters:
            msg   – a string describing the error
                    e.g. "Division by zero!"
            occur – True if the exception actually happened,
                    False if it is just a placeholder (default: True)
        """
        self.message = msg   # The error description
        self.occur   = occur # Did this exception actually happen?
        self.ret     = None  # Optional: a value to return instead of crashing


    def dispMSG(self):
        """
        Print the exception message to the screen.
        Call this when you want to show the error to the user.
        """
        print(self.message)


    def isOccur(self):
        """
        Check whether this exception actually happened.

        Returns:
            True  → the exception occurred (something went wrong)
            False → no exception, everything is fine
        """
        return self.occur


    def setReturn(self, value):
        """
        Store a special return value for this exception.

        Used when the program should return something meaningful
        instead of just crashing. For example:
          - Division of 0 / 0  → return 'Infinity'
          - Division of x / 0  → return 'undefined'

        Parameters:
            value – the value to return when this exception happens
        """
        self.ret = value


    def getReturn(self):
        """
        Retrieve the special return value for this exception.

        Returns:
            Whatever was set by setReturn() — e.g. 'Infinity' or 'undefined'
        """
        return self.ret


# =============================================================
#  Julo adds the Program class below this line
# =============================================================
