#! /usr/bin/python3
import ply.yacc as yacc

from oppy.opparser import (OpTqlParser, OpFilter, OpFuzzy,
                           OpUnionOperator, OpIntersectionOperator)


class OpResponse(object):
    def __init__(self, copy_from=None):
        if copy_from is None:
            self._objects = []
        else:
            self._objects = [obj for obj in copy_from]

    def __repr__(self):
        names = (obj.get('uuid') for obj in self._objects)
        return '<OpResponse [%s]>' % ', '.join(names)

    def __iter__(self):
        return iter(self._objects)

    def __contains__(self, obj):
        return obj in self._objects

    def __and__(self, other):
        response = OpResponse()
        for obj in self:
            if obj in other:
                obj = obj.copy()
                response.add(obj)
        return response

    def __or__(self, other):
        response = OpResponse()
        for obj in other:
            if obj in self:
                obj = obj.copy()
            response.add(obj)
        for obj in self:
            if obj not in response:
                response.add(obj)
        return response

    def __len__(self):
        return len(self._objects)

    def copy(self):
        return OpResponse(self)

    def _find_value_by_key(self, obj, tag):
        """ Find the value corresponding to the tag in nested dict """
        d = obj
        for key in tag.split('.'):
            d = d[key]
        return d

    def _find_value(self, obj_values, cmp_func):
        """ Raise ValueError if obj has not the value. """
        for val in obj_values:
            if isinstance(val, (int, float, str)):
                if cmp_func(val):
                    return True
            elif isinstance(val, dict):
                if self._find_value(val.values(), cmp_func):
                    return True
            elif isinstance(val, (tuple, list)):
                if self._find_value(val, cmp_func):
                    return True
        return False

    def filter(self, tag, cmp_func):
        """ Filter value of specified tag using the provided comparison function.
        """
        matching = OpResponse()
        for obj in self:
            try:
                tag_value = self._find_value_by_key(obj, tag)
            except KeyError:
                continue
            else:
                if cmp_func(tag_value):
                    matching.add(obj)
        return matching

    def fuzzy(self, cmp_func):
        matching = OpResponse()
        for obj in self:
            if self._find_value(obj.values(), cmp_func):
                matching.add(obj)
        return matching

    def add(self, obj):
        """ Add an object in the response.
        :param obj: the object to add to the response
        """
        if obj not in self._objects:
            self._objects.append(obj)


class OpDatabase(object):
    def __init__(self, objects):
        self._objects = objects

    def raw_query(self, tql):
        if isinstance(tql, str):
            tql = OpTqlParser(tql, debug=False, write_tables=False,
                              errorlog=yacc.NullLogger()).parse()
            evaluated = self._evaluate_ast(tql)
        elif tql is None:
            evaluated = OpResponse(self._objects)
        return evaluated

    # TQL AST evaluation:
    #
    def _evaluate_ast(self, ast):
        objects = OpResponse(self._objects)
        return self._evaluate_expression(objects, ast.expression)

    def _evaluate_expression(self, objects, expression):
        if isinstance(expression, OpFilter):
            return self._evaluate_filter(objects, expression)
        elif isinstance(expression, OpFuzzy):
            return self._evaluate_fuzzy(objects, expression)
        elif isinstance(expression, OpUnionOperator):
            return self._evaluate_union(objects, expression)
        elif isinstance(expression, OpIntersectionOperator):
            return self._evaluate_intersection(objects, expression)

    def _evaluate_filter(self, objects, filter):
        return objects.filter(filter.name, filter.match)

    def _evaluate_fuzzy(self, objects, filter):
        return objects.fuzzy(filter.match)

    def _evaluate_union(self, objects, union):
        left = self._evaluate_expression(objects, union.left_expression)
        right = self._evaluate_expression(objects, union.right_expression)
        return left | right

    def _evaluate_intersection(self, objects, intersection):
        left = self._evaluate_expression(objects, intersection.left_expression)
        right = self._evaluate_expression(objects,
                                          intersection.right_expression)
        return left & right
