from error import LineFieldsError, InstructionError, UndefinedSymbolError


class Instr(object):
    def __init__(self, opcode, format, operands):
        self._opcode = opcode
        self._format = format
        self._operands = operands

    @property
    def opcode(self):
        return self._opcode

    @property
    def format(self):
        return self._format

    @property
    def operands(self):
        return self._operands


OpTable = {
    'ADD':     Instr('18', 3, ['m']),
    'ADDF':    Instr('58', 3, ['m']),
    'ADDR':    Instr('90', 2, ['r1', 'r2']),
    'AND':     Instr('40', 3, ['m']),
    'CLEAR':   Instr('B4', 2, ['r1']),
    'COMP':    Instr('28', 3, ['m']),
    'COMPF':   Instr('88', 3, ['m']),
    'COMPR':   Instr('A0', 2, ['r1', 'r2']),
    'DIV':     Instr('24', 3, ['m']),
    'DIVF':    Instr('64', 3, ['m']),
    'DIVR':    Instr('9C', 2, ['r1', 'r2']),
    'FIX':     Instr('C4', 1, None),
    'FLOAT':   Instr('C0', 1, None),
    'HIO':     Instr('F4', 1, None),
    'J':       Instr('3C', 3, ['m']),
    'JEQ':     Instr('30', 3, ['m']),
    'JGT':     Instr('34', 3, ['m']),
    'JLT':     Instr('38', 3, ['m']),
    'JSUB':    Instr('48', 3, ['m']),
    'LDA':     Instr('00', 3, ['m']),
    'LDB':     Instr('68', 3, ['m']),
    'LDCH':    Instr('50', 3, ['m']),
    'LDF':     Instr('70', 3, ['m']),
    'LDL':     Instr('08', 3, ['m']),
    'LDS':     Instr('6C', 3, ['m']),
    'LDT':     Instr('74', 3, ['m']),
    'LDX':     Instr('04', 3, ['m']),
    'LPS':     Instr('D0', 3, ['m']),
    'MULF':    Instr('60', 3, ['m']),
    'MULR':    Instr('98', 2, ['r1', 'r2']),
    'NORM':    Instr('C8', 1, None),
    'OR':      Instr('44', 3, ['m']),
    'RD':      Instr('D8', 3, ['m']),
    'RMO':     Instr('AC', 2, ['r1', 'r2']),
    'RSUB':    Instr('4C', 3, None),
    'SHIFTL':  Instr('A4', 2, ['r1', 'n']),
    'SHIFTR':  Instr('A8', 2, ['r1', 'n']),
    'SIO':     Instr('F0', 1, None),
    'SSK':     Instr('EC', 3, ['m']),
    'STA':     Instr('0C', 3, ['m']),
    'STB':     Instr('78', 3, ['m']),
    'STCH':    Instr('54', 3, ['m']),
    'STF':     Instr('80', 3, ['m']),
    'STI':     Instr('D4', 3, ['m']),
    'STL':     Instr('14', 3, ['m']),
    'STS':     Instr('7C', 3, ['m']),
    'STSW':    Instr('E8', 3, ['m']),
    'STT':     Instr('84', 3, ['m']),
    'STX':     Instr('10', 3, ['m']),
    'SUB':     Instr('1C', 3, ['m']),
    'SUBF':    Instr('5C', 3, ['m']),
    'SUBR':    Instr('94', 2, ['r1', 'r2']),
    'SVC':     Instr('B0', 2, ['n']),
    'TD':      Instr('E0', 3, ['m']),
    'TIO':     Instr('F8', 1, None),
    'TIX':     Instr('2C', 3, ['m']),
    'TIXR':    Instr('B8', 2, ['r1']),
    'WD':      Instr('DC', 3, ['m'])
}

flagTable = {
    'n': 0b100000,
    'i': 0b010000,
    'x': 0b001000,
    'b': 0b000100,
    'p': 0b000010,
    'e': 0b000001
}

registerTable = {
    'A':  0,
    'X':  1,
    'L':  2,
    'B':  3,
    'S':  4,
    'T':  5,
    'F':  6,
    'PC': 8,
    'SW': 9
}


class Format(object):
    def generate(self):
        raise NotImplementedError


class Format1(Format):
    def __init__(self, mnemonic):
        self._mnemonic = mnemonic

    def generate(self):
        if self._mnemonic is None:
            raise LineFieldsError('A mnemonic was not specified.')

        output = OpTable[self._mnemonic].opcode

        return self._mnemonic, None, output


class Format2(Format):
    def __init__(self, mnemonic, r1, r2):
        self._mnemonic = mnemonic
        self._r1 = r1
        self._r2 = r2

    def generate(self):
        if self._mnemonic is None:
            raise LineFieldsError('A mnemonic was not specified.')

        output = ''

        output += OpTable[self._mnemonic].opcode

        r1_lookup = registerTable[self._r1]
        r1_lookup = str(hex(r1_lookup)).lstrip('0x') or 0
        output += str(r1_lookup)

        if self._r2 is not None:
            r2_lookup = registerTable[self._r2]
            r2_lookup = str(hex(r2_lookup)).lstrip('0x') or 0
            output += str(r2_lookup)
        else:
            output += '0'

        return self._mnemonic, (self._r1, self._r2), output


class Format3(Format):
    def __init__(self, base, symtab, line):
        self._base = base
        self._symtab = symtab
        self._location = line.location
        self._mnemonic = line.mnemonic
        self._operand = line.operand
        self._disp = None
        self._flags, self._n, self._i = check_flags(line)
        self._contents = line

    def generate(self):
        if self._mnemonic is None:
            raise LineFieldsError('A mnemonic was not specified.')

        is_digit = False
        has_operand = False

        if self._operand is not None:
            has_operand = True
            if indexed(self._operand):
                self._operand = self._operand[0]
                TA = self._symtab.get(self._operand)
            elif indirect(self._operand):
                self._operand = self._operand[1:]
                TA = self._symtab.get(self._operand)
            elif immediate(self._contents.operand):
                self._operand = self._contents.operand[1:]
                if self._operand.isdigit():
                    TA = self._operand
                    is_digit = True
                else:
                    TA = self._symtab.get(self._operand)
            elif literal(self._operand):
                TA = parseLiteral(self._operand)
            else:
                TA = self._symtab.get(self._operand)

            if TA:
                self._disp = TA
            else:
                raise UndefinedSymbolError('Undefined symbol: {}'.format(self._contents.operand))

        else:
            self._disp = 0

        if not is_digit and has_operand:
            pc = int(self._location) + 3
            disp = int(str(self._disp), 16) - pc

            if -2048 <= disp <= 2047:
                self._flags += flagTable['p']
                disp = twos_complement(disp, 12)
            else:
                if self._base is None:
                    raise InstructionError('BASE directive has not been not set.')
                base = int(str(self._base), 16)
                disp = int(str(self._disp), 16) - base

                if disp < 0 or disp > 4095:
                    raise InstructionError('Neither PC relative or Base relative could be used.')
                self._flags += flagTable['b']
                disp = to_binary(disp).zfill(12)

        else:
            disp = twos_complement(int(self._disp), 12)

        op = int(OpTable[self._mnemonic].opcode, 16)
        if self._n:
            op += 2
        if self._i:
            op += 1
        op = twos_complement(op, 6)

        output = ''
        output += op
        output += to_binary(hex(self._flags)).zfill(4)
        output += disp
        hex_output = hex(int(output, 2))[2:].zfill(6).upper()

        return self._mnemonic, self._disp, hex_output


class Format4(Format):
    def __init__(self, symtab, line):
        self._symtab = symtab
        self._location = line.location
        self._mnemonic = line.mnemonic[1:]
        self._operand = line.operand
        self._flags, self._n, self._i = check_flags(line)
        self._contents = line

    def generate(self):
        if self._mnemonic is None:
            raise LineFieldsError('A mnemonic was not specified.')

        if self._operand is not None:
            if immediate(self._contents.operand):
                self._operand = self._contents.operand[1:]
                if str(self._operand).isdigit():
                    TA = hex(int(self._operand))[2:]
                else:
                    TA = self._symtab.get(self._operand)
            elif indexed(self._operand):
                self._operand = self._operand[0]
                TA = self._symtab.get(self._operand)
            else:
                TA = self._symtab.get(self._operand)

            if TA:
                self._disp = TA
            else:
                raise UndefinedSymbolError('Undefined symbol: {}'.format(self._operand))
        else:
            self._disp = 0

        op = int(str(OpTable[self._mnemonic].opcode), 16)
        if self._n:
            op += 2
        if self._i:
            op += 1
        op = twos_complement(op, 6)

        output = ''
        output += op
        output += to_binary(hex(self._flags)).zfill(4)
        output += twos_complement(int(self._disp, 16), 20)

        hex_output = hex(int(output, 2))[2:].zfill(6).upper()

        return self._mnemonic, self._disp, hex_output

    def relocate(self):
        relocate = False

        if immediate(self._contents.operand):
            self._operand = self._contents.operand[1:]
            if not str(self._disp).isdigit():
                TA = self._symtab.get(self._disp)
                relocate = True
        elif indexed(self._operand):
            self._operand = self._operand[0]
            TA = self._symtab[self._operand]
            relocate = True
        else:
            TA = self._symtab.get(self._operand)
            relocate = True if TA is not None else False

        return relocate


def sic_format(symtab, mnemonic, operand):
    op = OpTable[mnemonic].opcode

    if operand is None:
        TA = str(0).zfill(4)
    elif indexed(operand):
        TA = bin(int(symtab[operand[0]], 16))[2:].zfill(15)
        TA = hex(int(('1' + TA), 2))[2:]
    else:
        TA = symtab[operand][2:]

    return op+TA


# indexed addressing
def indexed(x): return isinstance(x, list) and x[1] == 'X'


# immediate addressing
def immediate(x): return str(x).startswith('#')


# indirect addressing
def indirect(x): return str(x).startswith('@')


# Extended _format
def extended(x): return str(x).startswith('+')


# Literal
def literal(x): return str(x).startswith('=')


def to_binary(hex_string):
    return bin(int(str(hex_string), 16))[2:]


def twos_complement(value, bits):
    if value < 0:
        value = (1 << bits) + value
    out_format = '{:0%ib}' % bits

    return out_format.format(value)


def check_flags(line):
    flags = 0
    n = False
    i = False

    if line.operand is None:
        return flags, n, i

    if immediate(line.operand):
        i = True
    elif indirect(line.operand):
        n = True
    else:
        n, i = True, True

    if indexed(line.operand):
        if not n or not i:
            raise LineFieldsError(
                message="Indexed addressing cannot be used with"
                + " immediate or indirect addressing modes.")
        else:
            flags += flagTable['x']

    if extended(line.mnemonic):
        flags += flagTable['e']

    return flags, n, i


def parseLiteral(operand):
    if operand.startswith('X'):
        value = operand.replace('X', '')
        stripped = value.replace("'", '')
        TA = int(stripped, 16)
    elif operand.startswith('C'):
        value = operand.replace('C', '')
        stripped = value.replace("'", '')
        TA = ''
        for c in stripped:
            TA += format(ord(c), 'x')
    else:
        raise LineFieldsError("Literal prefix error: {}".format(operand))

    return TA
