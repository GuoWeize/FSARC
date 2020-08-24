# -*- coding: utf-8 -*-
"""
This file provides functions to detect conflicts among requirement tuples.

Function 'detect' is the interface for detetcing conflicts among requirement tuples.
"""
import os, types, yaml
from typing import Dict, Set, Tuple

from config import rules_yaml
from FSARC.Requirement import *


def list_eq(a: list, b: list) -> bool:
    return len(set(a)) == len(set(b)) == len(set(a) | set(b))

def list_gt(a: list, b:list) -> bool:
    return len(set(a)) == len(set(a) | set(b))


class Operators:
    with open('..' + os.path.sep + rules_yaml, encoding='utf-8') as f:
        file_content = yaml.load(f.read())
    type: Dict[str, str]
    allowed_types: Dict[str, List[str]]
    equal_rules: Dict[str, types.LambdaType]
    include_rules: Dict[str, types.LambdaType]
    contradict_rules: Dict[str, types.LambdaType]

    @classmethod
    def initial(cls):
        cls.type = cls.file_content['field types']
        cls.allowed_types = cls.file_content['allowed types']
        operators: Dict[str, dict] = cls.file_content['operators']
        cls.equal_rules = {key: eval(value) for key, value in operators['equal'].items()}
        cls.include_rules = {key: eval(value) for key, value in operators['include'].items()}
        cls.contradict_rules = {key: eval(value) for key, value in operators['contradict'].items()}
        cls.operator_rules = {
            'equal': cls.equal_rules,
            'include': cls.include_rules,
            'contradict': cls.contradict_rules,
        }

    @classmethod
    def O(cls, object1, field1, relation, object2, field2) -> bool:
        tuple1, tuple2 = getattr(object1, field1, None), getattr(object2, field2, None)
        if tuple1 is None or tuple2 is None:
            raise TypeError()
        if cls.type[field1] != cls.type[field2]:
            raise TypeError()
        Type = cls.type[field1]
        if Type not in cls.allowed_types[relation]:
            raise TypeError()
        return getattr(Operators, relation)[Type](tuple1, tuple2)

    @classmethod
    def condition_set_include(cls, a: List[Condition], b: List[Condition]) -> bool:
        rule = cls.file_content['rules']['condition include']
        lambda_func = Rules.parse_rule(rule)
        return any([lambda_func(c2, c1) for c1 in a for c2 in b])

    @classmethod
    def entity_set_include(cls, a: List[Entity], b: List[Entity]) -> bool:
        lambda_func = Operators.include_rules['entity']
        return all([any([lambda_func(entity_a, entity_b) for entity_a in a]) for entity_b in b])

    @classmethod
    def condition_contradict(cls, a: List[Condition]) -> bool:
        rule = cls.file_content['rules']['condition contradict']
        lambda_func = Rules.parse_rule(rule)
        return any([lambda_func(c1, c2) for c1 in a for c2 in a])


class Rules:
    rule_lambdas = {}

    @classmethod
    def judge(cls, req1: Req, req2: Req, rule_name: str) -> bool:
        return cls.rule_lambdas[rule_name](req1, req2)

    @classmethod
    def initial(cls):
        with open('..' + os.path.sep + rules_yaml, encoding='utf-8') as f:
            file_content = yaml.load(f.read())
        rules: dict = file_content['rules']
        for rule_name, rule in rules.items():
            cls.rule_lambdas[rule_name] = cls.parse_rule(rule)
        cls.input_output_interlock()

    @classmethod
    def parse_rule(cls, rule) -> types.LambdaType:
        if type(rule) == dict:
            label = list(rule.keys())[0]
            content = rule[label]
            if label == 'or':
                return cls.parse_or([cls.parse_rule(sub_rule) for sub_rule in content])
            elif label == 'and':
                return cls.parse_and([cls.parse_rule(sub_rule) for sub_rule in content])
            elif label == 'not':
                return cls.parse_not(cls.parse_rule(content))
            elif label == 'function':
                return cls.rule_lambdas[content]
            elif label == 'for':
                return cls.parse_for(content)
            else:
                raise SyntaxError()
        else:
            return cls.parse_single_rule(rule)

    @classmethod
    def parse_or(cls, lambda_list: List[types.LambdaType]) -> types.LambdaType:
        return lambda x, y: any([f(x, y) for f in lambda_list])

    @classmethod
    def parse_and(cls, lambda_list: List[types.LambdaType]) -> types.LambdaType:
        return lambda x, y: all([f(x, y) for f in lambda_list])

    @classmethod
    def parse_not(cls, lambda_func: types.LambdaType) -> types.LambdaType:
        return lambda x, y: not lambda_func(x, y)

    @classmethod
    def parse_for(cls, content) -> types.LambdaType:
        rule_in_for = cls.parse_rule(content['condition'])
        label, index, filed = content['label'], content['index'], content['field']
        if (label, index) == ('or', '1'):
            return lambda x, y: any([rule_in_for(obj, y) for obj in getattr(x, filed)])
        elif (label, index) == ('or', '2'):
            return lambda x, y: any([rule_in_for(y, obj) for obj in getattr(x, filed)])
        elif (label, index) == ('and', '1'):
            return lambda x, y: all([rule_in_for(obj, y) for obj in getattr(x, filed)])
        elif (label, index) == ('and', '2'):
            return lambda x, y: all([rule_in_for(y, obj) for obj in getattr(x, filed)])
        else:
            SyntaxError()

    @classmethod
    def parse_single_rule(cls, rule) -> types.LambdaType:
        index1, field1, relation, index2, field2 = tuple(rule.split(' '))
        if (index1, index2) == ('1', '1'):
            return lambda x, y: Operators.O(x, field1, relation, x, field2)
        elif (index1, index2) == ('1', '2'):
            return lambda x, y: Operators.O(x, field1, relation, y, field2)
        elif (index1, index2) == ('2', '1'):
            return lambda x, y: Operators.O(y, field1, relation, x, field2)
        elif (index1, index2) == ('2', '2'):
            return lambda x, y: Operators.O(y, field1, relation, y, field2)
        else:
            raise SyntaxError()

    @classmethod
    def input_output_interlock(cls):
        event_inconsistency = lambda x, y: not cls.rule_lambdas['event inconsistency'](x, y) \
                                       and not cls.rule_lambdas['event inconsistency'](y, x)
        entity_inclusion = lambda x, y: \
            any([Operators.include_rules['entity'](e1, e2) for e1 in x.output for e2 in y.input])
        cls.rule_lambdas['input output interlock'] = \
            lambda x, y: event_inconsistency(x, y) and entity_inclusion(x, y)


class Detector:
    conflicts = []
    operation_event_graph, input_output_graph = {}, {}

    @classmethod
    def detect(cls, requirements: List[Req]) -> List[Tuple[str, List[Req]]]:
        """
        conflict detecting function
        :param requirements: all modelled requiremnts for conflict detetcting
        :return: conflict results, (conflict type, [req1, req2, ...])
        """
        print('conflict detecting ...')
        cls.initial(len(requirements))
        cls.traverse_req(requirements)
        cls.detect_interlock(requirements)
        print('conflict detecting finished.')
        return cls.conflicts

    @classmethod
    def initial(cls, length):
        Operators.initial()
        Rules.initial()
        cls.conflicts = []
        cls.operation_event_graph, cls.input_output_graph = {}, {}
        for index in range(length):
            cls.operation_event_graph[index] = []
            cls.input_output_graph[index] = []

    @classmethod
    def traverse_req(cls, requirements):
        for index1, req1 in enumerate(requirements):
            for index2 in range(index1 + 1, len(requirements)):
                req2 = requirements[index2]
                if req1.groupid == req2.groupid != 0:
                    continue
                for rule in ['operation inconsistency', 'restriction inconsistency', 'event inconsistency']:
                    if Rules.judge(req1, req2, rule):
                        cls.conflicts.append((rule, [req1, req2]))
                for rule in ['operation inclusion', 'event inclusion']:
                    if Rules.judge(req1, req2, rule):
                        cls.conflicts.append((rule, [req1, req2]))
                    elif Rules.judge(req2, req1, rule):
                        cls.conflicts.append((rule, [req2, req1]))
                for r_begin, r_end, begin, end in [(req1, req2, index1, index2),
                                                   (req2, req1, index2, index1)]:
                    if Rules.judge(r_begin, r_end, 'operation event interlock'):
                        cls.operation_event_graph[begin].append(end)
                for r_begin, r_end, begin, end in [(req1, req2, index1, index2),
                                                   (req2, req1, index2, index1)]:
                    if Rules.judge(r_begin, r_end, 'input output interlock'):
                        cls.input_output_graph[begin].append(end)

    @classmethod
    def detect_interlock(cls, requirements):
        operation_event_loops = cls.find_loop(cls.operation_event_graph)
        input_output_loops = cls.find_loop(cls.input_output_graph)
        for loops, name in [(operation_event_loops, 'operation event interlock'),
                            (input_output_loops, 'input output interlock')]:
            for loop in loops:
                if len(loop) > 1:
                    loop_list = list(loop)
                    list.sort(loop_list)
                    cls.conflicts.append((name, [requirements[i] for i in loop_list]))

    @classmethod
    def find_loop(cls, chain: Dict[int, List[int]]) -> List[Set[int]]:
        n = len(chain.keys())
        visited = [False] * n
        trace = []
        result = []

        def findCycle(v):
            if visited[v]:
                if v in trace:
                    j = trace.index(v)
                    s = set(trace[j:])
                    flag = True
                    for r in result:
                        if len(r & s) == len(s):
                            flag = False
                            break
                    if flag:
                        for r in result:
                            if len(r & s) == len(r):
                                result.remove(r)
                        result.append(s)
                    return
                return
            visited[v] = True
            trace.append(v)
            for i in chain[v]:
                findCycle(i)
            if len(trace) > 0:
                trace.pop()

        for now in range(n):
            visited = [False] * n
            trace = []
            findCycle(now)
        return result
