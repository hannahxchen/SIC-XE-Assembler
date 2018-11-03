from instructions import Format, Format4

directives = ['START', 'END', 'RESB', 'RESW', 'BASE']


def outputLST(filename, start_addr, asmlines, obj_code, mode):
    with open(filename+'.lst', 'w') as f:
        count = 0
        for line in asmlines:
            loc = line.location if line.location else start_addr
            loc = '' if line.mnemonic == 'END' else format(loc, 'x').zfill(4).upper()
            label = '' if line.label is None else line.label
            mnemonic = line.mnemonic

            if line.operand is None:
                operand = ''
            elif isinstance(line.operand, str):
                operand = line.operand
            else:
                operand = ','.join(line.operand)

            if mnemonic in directives:
                obj = ''
            else:
                obj = obj_code[count][1]
                count += 1

                if mode == 'sicxe':
                    if isinstance(obj, tuple):
                        obj = obj[-1]
                    else:
                        obj = obj.generate()[2]
                else:
                    if isinstance(obj, tuple):
                        obj = obj[-1]

            print(loc.ljust(10), label.ljust(10), mnemonic.ljust(10), operand.ljust(10), obj.ljust(10))
            f.write('{0}{1}{2}{3}{4}\n'.format(loc.ljust(10), label.ljust(10), mnemonic.ljust(10), operand.ljust(10), obj.ljust(8)))


def gen_header(program_name, start_addr, program_length):
    start_addr = hex(start_addr)[2:].zfill(6).upper()
    return 'H{0}{1}{2}'.format(program_name.ljust(6), start_addr, program_length)


def gen_text_sicxe(generated_code, start_addr):
    code = list(generated_code)
    generated_lines = []
    modified = []
    length = 60

    next_addr = code[0][0]
    temp_length = 0

    while len(code) > 0:
        temp_line = ''
        temp_start_addr = next_addr
        while(len(temp_line) <= length):
            x = code.pop(0)
            if isinstance(x[1], Format):
                temp = x[1].generate()[2].upper()
            else:
                temp = x[1][2].upper()

            temp_line += temp

            if isinstance(x[1], Format4):
                if x[1].relocate():
                    relative_addr = hex(x[0] - start_addr + 1)[2:].zfill(6).upper()
                    relocate_length = '05'
                    modified.append('M{}{}'.format(relative_addr, relocate_length))

            if len(code) == 0:
                break

        if len(code) == 0:
            temp_length = hex(x[0] - temp_start_addr)[2:].zfill(2).upper()
        else:
            next_addr = code[0][0]
            temp_length = hex(next_addr - temp_start_addr)[2:].zfill(2).upper()
        temp_start_addr = hex(temp_start_addr - start_addr)[2:].zfill(6).upper()
        output = 'T{}{}{}'.format(temp_start_addr, temp_length, temp_line)

        generated_lines.append(output)
        temp_length = 0

    return generated_lines, modified


def gen_text_sic(object_code, symtab, start_addr):
    generated_lines = []
    code = list(object_code)
    length = 60

    next_addr = object_code[0][0]
    temp_length = 0

    while len(code) > 0:
        temp_line = ''
        temp_start_addr = next_addr
        while(len(temp_line) <= length):
            x = code.pop(0)

            if isinstance(x[1], tuple):
                temp = x[1][-1]
            else:
                temp = x[1].upper()

            temp_line += temp

            if len(code) == 0:
                break

        if len(code) == 0:
            temp_length = hex(x[0] - temp_start_addr)[2:].zfill(2).upper()
        else:
            next_addr = code[0][0]
            temp_length = hex(next_addr - temp_start_addr)[2:].zfill(2).upper()
        temp_start_addr = hex(temp_start_addr - start_addr)[2:].zfill(6).upper()
        output = 'T{}{}{}'.format(temp_start_addr, temp_length, temp_line)

        generated_lines.append(output)
        temp_length = 0

    return generated_lines, None


def gen_end(start_addr):
    return 'E{}'.format(hex(start_addr)[2:].zfill(6).upper())


def generate_records(filename, program_name, start_addr, object_code, symtab, mode):
    program_length = hex(object_code[-1][0] - start_addr + 1)[2:].zfill(6).upper()
    head = gen_header(program_name, start_addr, program_length)
    if mode == 'sic':
        text, relocate = gen_text_sic(object_code, symtab, start_addr)
    else:
        text, relocate = gen_text_sicxe(object_code, start_addr)
    end = gen_end(start_addr)

    with open(filename+'.obj', 'w') as f:
        f.write(head + '\n')
        f.write('\n'.join(text) + '\n')
        if relocate:
            f.write('\n'.join(relocate) + '\n')
        f.write(end)
