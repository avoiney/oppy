#! /usr/bin/python3
import ply.lex as lex


class OpTqlLexer(object):
    tokens = (
        'NUMBER',
        'STRING',
        'NAME',
        'EQUALS',
        'AND',
        'OR',
        'LPAREN',
        'RPAREN'
    )
    t_NAME = r'[a-zA-Z\.]+'
    t_AND = r'&'
    t_OR = r'\|'
    t_EQUALS = r'='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'

    # A string containing ignored characters (spaces and tabs)
    t_ignore = ' \t'

    def __init__(self, **kwargs):
        self._lexer = lex.lex(module=self, **kwargs)

    def t_NUMBER(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_STRING(self, t):
        r'"[a-zA-Z0-9\- \*:/\.]+"'
        t.value = t.value.strip('"')
        return t

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def input(self, _input):
        self._current_input = _input
        return self._lexer.input(_input)

    def __getattr__(self, name):
        lexer = super(OpTqlLexer, self).__getattribute__('_lexer')
        attr = getattr(lexer, name)
        if attr is None:
            raise AttributeError("'%s' object has no attribute '%s'" % (self,
                                                                        name))
        else:
            return attr
