class Error(Exception):
    pass


class LineFieldsError(Error):
    pass


class DuplicateSymbolError(Error):
    pass


class OpcodeLookupError(Error):
    pass


class UndefinedSymbolError(Error):
    pass


class InstructionError(Error):
    pass


class InputError(Error):
    pass
