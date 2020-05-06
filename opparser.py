#! /usr/bin/python3
import ply.yacc as yacc
import re

from oplex import OpTqlLexer


class ParsingError(Exception):
    pass


class OpTqlAst(object):
    def __init__(self, expression=None):
        self.expression = expression


class OpFilter(object):
    def __init__(self, name, value=None):
        self.name = name
        self.value = '^' + str(value).replace('*', '.*') + '$'

    def __repr__(self):
        return '{}={}'.format(self.name, self.value)

    def match(self, value):
        if value is None:
            return self.value is None
        return re.match(self.value, value) is not None


class OpFuzzy(object):
    def __init__(self, value):
        self.value = '^' + str(value).replace('*', '.*') + '$'

    def __repr__(self):
        return '{}'.format(self.value)

    def match(self, value):
        if value is None:
            return self.value is None
        return re.match(self.value, '{}'.format(value), re.IGNORECASE) is not None


class OpBinaryOperator(object):
    SYMBOL = '?'

    def __init__(self, left_expression, right_expression):
        self.left_expression = left_expression
        self.right_expression = right_expression

    def __repr__(self):
        return '{}{}{}'.format(self.left_expression, self.SYMBOL,
                               self.right_expression)


class OpUnionOperator(OpBinaryOperator):
    SYMBOL = '|'


class OpIntersectionOperator(OpBinaryOperator):
    SYMBOL = '&'


class OpTqlParser(object):
    """Parser for TQL grammar
    """
    tokens = OpTqlLexer.tokens

    precedence = (('left', 'OR', 'AND'),)

    def __init__(self, _input, **kwargs):
        self._input = _input
        self._lexer = kwargs.pop('lexer', OpTqlLexer())
        self._parser = yacc.yacc(module=self, **kwargs)

    start = 'input'

    def p_input(self, p):
        """input : expr"""
        if len(p) == 1:
            p[0] = OpTqlAst()
        else:
            p[0] = OpTqlAst(p[1])

    def p_expr_fuzzy(self, p):
        """ expr : STRING
                 | NAME
                 | NUMBER """
        p[0] = OpFuzzy(p[1])

    def p_expr_pair(self, p):
        """expr : NAME EQUALS STRING
                | NAME EQUALS NUMBER"""
        p[0] = OpFilter(p[1], p[3])

    def p_expr_par(self, p):
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]

    def p_expr_binary(self, p):
        """expr : expr OR expr
                | expr AND expr"""
        if p[2] == '|':
            p[0] = OpUnionOperator(p[1], p[3])
        elif p[2] == '&':
            p[0] = OpIntersectionOperator(p[1], p[3])

    def p_error(self, token):
        if token is None:
            raise ParsingError('Syntax error near of "EOL"')
        else:
            raise ParsingError('Syntax error near of "%s"' % token.value)

    def parse(self):
        return self._parser.parse(self._input, self._lexer, tracking=True)

    def __getattr__(self, name):
        parser = super(OpTqlParser, self).__getattribute__('_parser')
        attr = getattr(parser, name)
        if attr is None:
            raise AttributeError("'%s' object has no attribute '%s'" % (self,
                                                                        name))
        else:
            return attr
