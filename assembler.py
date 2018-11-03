import sys
from instructions import Format1, Format2, Format3, Format4
from instructions import OpTable, extended, sic_format
from error import DuplicateSymbolError, LineFieldsError, OpcodeLookupError, InputError
from records import outputLST, generate_records

symtab = {}
base = None
start_addr = 0
program_length = 0
program_name = ""
asmlines = []


def open_file():
    if len(sys.argv) != 3:
        raise InputError(
            "\nInput Error! Input example:\n" +
            "SIC mode: FILENAME.ASM -sic\n" +
            "SIC/XE mode:FILENAME.ASM -sicxe")
    elif not sys.argv[1].lower().endswith('.asm'):
        raise InputError("File format should be .asm")
    elif sys.argv[2][1:] != 'sic' and sys.argv[2][1:] != 'sicxe':
        raise InputError("Input Mode Error.")
    else:
        filename = sys.argv[1][:-4]
        mode = sys.argv[2][1:]

        if mode != 'sic' or mode != 'sicxe':
            print()
        try:
            with open(sys.argv[1]) as f:
                asmlines = f.readlines()
                # remove comments
                asmlines = [x[:x.find('.')].strip() for x in asmlines]
                # remove empty elements and split lines with tabs
                asmlines = [x.split() for x in asmlines if x is not '']

                return filename, mode, asmlines
        except IOError:
            print("Cannot find the file!")


class srcline(object):
    def __init__(self, label, mnemonic, operand):
        self.label = label
        self.mnemonic = mnemonic
        self.operand = operand
        self.location = None

    def parse(line):
        if len(line) > 1 and ',' in line[len(line)-1]:
            operands = line[len(line)-1].split(',')
        elif len(line) > 1:
            operands = line[len(line)-1]

        if len(line) is 3:
            return srcline(label=line[0], mnemonic=line[1], operand=operands)

        elif len(line) is 2:
            return srcline(label=None, mnemonic=line[0], operand=operands)

        elif len(line) is 1:
            return srcline(label=None, mnemonic=line[0], operand=None)

        else:
            raise LineFieldsError('Invalid amount of fields on line: ', line)


def first_pass(asmlines):
    global start_addr
    global program_name

    firstline = asmlines[0]
    displayLine(firstline)

    # read first line and check 'START' opcode
    if firstline.mnemonic is not None:
        if firstline.mnemonic == 'START':
            start_addr = int(firstline.operand, 16)
            locctr = int(firstline.operand, 16)
            program_name = firstline.label
        else:
            locctr = 0

    for line in asmlines[1:]:
        displayLine(line)
        line.location = locctr
        if line.label is not None:
            if line.label not in symtab:
                symtab[line.label] = hex(locctr)
            else:
                raise DuplicateSymbolError('A duplicate symbol was found: {}'.format(line.label))

        mnemonic = base_mnemonic(line.mnemonic)
        # Search OpTable for mnemonic
        if mnemonic in OpTable:
            locctr += determine_format(line.mnemonic)
        elif mnemonic == 'WORD':
            locctr += 3
        elif mnemonic == 'RESW':
            locctr += 3*int(line.operand)
        elif mnemonic == 'RESB':
            locctr += int(line.operand)
        elif mnemonic == 'BYTE':
            if line.operand.startswith('X'):
                value = line.operand.replace('X', '')
                value = value.replace("'", '')
                hex_value = int(value, 16)
                locctr += int((len(hex(hex_value))-2)/2)
            elif line.operand.startswith('C'):
                value = line.operand.replace('C', '')
                value = value.replace("'", '')
                locctr += len(value)
            else:
                raise LineFieldsError('Invalid value for BYTE: {}'.format(line.operand))
        elif mnemonic == 'END':
            break
        elif mnemonic == 'BASE':
            pass
        else:
            raise OpcodeLookupError('The mnemonic "{}" is invalid.'.format(line.mnemonic))


def second_pass(asmlines, mode):
    global base
    object_code = []

    for line in asmlines:
        if OpTable.get(base_mnemonic(line.mnemonic)):
            if mode == 'sicxe':
                instr_format = determine_format(line.mnemonic)
                instr_output = generate_instruction(instr_format, line)
            else:
                instr_output = sic_format(symtab, line.mnemonic, line.operand)
            object_code.append((line.location, instr_output))
        else:
            if line.mnemonic == 'WORD':
                hex_value = hex(int(line.operand, 16))
                stripped = hex_value.lstrip('0x')
                padded = stripped.zfill(6)
                output = (line.mnemonic, line.operand, padded)
                object_code.append((line.location, output))
            elif line.mnemonic == 'BYTE':
                if line.operand.startswith('X'):
                    value = line.operand.replace('X', '')
                    stripped = value.replace("'", '')
                    output = (line.mnemonic, line.operand, stripped)
                    object_code.append((line.location, output))
                elif line.operand.startswith('C'):
                    value = line.operand.replace('C', '')
                    stripped = value.replace("'", '')
                    hex_value = ''
                    for c in stripped:
                        hex_value += format(ord(c), 'x').upper()
                    output = (line.mnemonic, line.operand, hex_value)
                    object_code.append((line.location, output))
            elif line.mnemonic == 'BASE':
                base = symtab.get(line.operand)
            elif line.mnemonic == 'NOBASE':
                base = None

    return object_code


def generate_instruction(instr_format, line):
    if instr_format is 1:
        instruction = Format1(mnemonic=line.mnemonic)
    elif instr_format is 2:
        op_num = OpTable[line.mnemonic].operands
        if len(op_num) == 2:
            r1, r2 = line.operand[0], line.operand[1]
        elif len(op_num) == 1:
            r1, r2 = line.operand, None
        instruction = Format2(mnemonic=line.mnemonic, r1=r1, r2=r2)
    elif instr_format is 3:
        instruction = Format3(base=base, symtab=symtab, line=line)
    elif instr_format is 4:
        instruction = Format4(symtab=symtab, line=line)

    return instruction


def base_mnemonic(mnemonic):
    if extended(mnemonic):
        return mnemonic[1:]
    else:
        return mnemonic


def determine_format(mnemonic):
    if extended(mnemonic):
        return OpTable[mnemonic[1:]].format+1
    else:
        return OpTable[mnemonic].format


def displayLine(line):
    label = line.label
    operand = line.operand

    if label is None:
        label = ''
    if operand is None:
        operand = ''
    elif isinstance(operand, list):
        operand = ','.join(operand)

    print(label.rjust(8), line.mnemonic.rjust(10), operand.rjust(10))


if __name__ == '__main__':
    filename, mode, data = open_file()
    for line in data:
        asmlines.append(srcline.parse(line))

    print('===================== First Pass =======================')
    first_pass(asmlines)
    print('\n===================== Symbol Table =====================')
    for sym, val in symtab.items():
        print(sym.rjust(8), val.rjust(10))
    print('\n===================== Second Pass =======================')

    object_code = second_pass(asmlines, mode)
    outputLST(filename, start_addr, asmlines, object_code, mode)
    generate_records(filename, program_name, start_addr, object_code, symtab, mode)
