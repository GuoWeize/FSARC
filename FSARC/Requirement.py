# -*- coding: utf-8 -*-
"""
This file provides classes for requirements data structure.
"""
from typing import List, Union

def str2tuples(tuples: List[str]) -> tuple:
    # agent
    agent = Entity.str2entity(tuples[0])
    # operation
    operation = Operation()
    predicate = tuples[1]
    if operation[:5] == 'ABLE ':
        operation.Able = True
        predicate = operation[5:]
    elif operation[:4] == 'NOT ':
        operation.Not = True
        predicate = operation[4:]
    operation.predicate = predicate
    # input & output
    entity_str_list = tuples[2].split(', ')
    Input = [Entity.str2entity(s) for s in entity_str_list]
    entity_str_list = tuples[3].split(', ')
    output = [Entity.str2entity(s) for s in entity_str_list]
    # restriction
    restriction = tuples[4].split(', ')
    return agent, operation, Input, output, restriction


class Operation:
    def __init__(self):
        self.predicate  : str   = ''
        self.Not        : bool  = False
        self.Able       : bool  = False
    def __repr__(self):
        return f"{'ABLE ' if self.Able else ''}{'NOT ' if self.Not else ''}{self.predicate}"


class Req:
    """
    Requirement 8 tuples:
    (id, groupid, event, agent, operation, input, output, restriction)
    """
    def __init__(self, reqid: int):
        self.reqid      : int               = reqid
        self.groupid    : int               = 0
        self.event      : List[Condition]   = []
        self.agent      : Entity            = Entity('')
        self.operation  : Operation         = Operation()
        self.input      : List[Entity]      = []
        self.output     : List[Entity]      = []
        self.restriction: List[str]         = []

    def __repr__(self):
        event = ', '.join([str(c) for c in self.event]) if len(self.event) != 0 else '*always*'
        return f'({self.reqid}) , ({self.groupid}) , ({event}) , {tuples_to_str(self)}\n'

    @classmethod
    def str2Req(cls, s: str):
        s = s[1: -1]
        s.replace('*void*', '')
        # event clause
        clause_list = []
        while (l_index := s.find('{')) > 0:
            r_index = s.find('}', l_index)
            clause_list.append(s[l_index + 1: r_index])
            s = s[: l_index] + s[r_index+1 :]
        tuples = s.split(') , (')
        req = cls(int(tuples[0]))
        req.groupid = int(tuples[1])
        # event
        event = tuples[2]
        if event != '*always*':
            req.event = [Condition.str2Condition(clause) for clause in clause_list]
        req.agent, req.operation, req.input, req.output, req.restriction = str2tuples(tuples[3:])
        return req


class Condition:
    """
    event clause 5 tuples:
    (agent, operation, input, output, restriction)
    """
    def __init__(self):
        self.agent      : Entity        = Entity('')
        self.operation  : Operation     = Operation()
        self.input      : List[Entity]  = []
        self.output     : List[Entity]  = []
        self.restriction: List[str]     = []

    def __repr__(self):
        return f'{{{tuples_to_str(self)}}}'

    @classmethod
    def str2Condition(cls, tuple_str: str):
        tuples = (tuple_str[1: -1]).split(') , (')
        c = Condition()
        c.agent, c.operation, c.input, c.output, c.restriction = str2tuples(tuples)
        return c


class Entity:
    """ entities in requirements """
    entities: list = []         # all entities in requirements

    def __init__(self, base: str):
        self.base       : str           = base
        self.modifier   : List[str]     = []
        self.is_all     : bool          = False
        self.parts      : List[Entity]  = []
        self.entirety   : Entity        = Entity('') if base != '' else None

    def __repr__(self):
        if self.base == '':
            return 'None'
        all_str = 'ALL ' if self.is_all else ''
        if self.modifier:
            modifier_str = '[' + ']['.join([str(e) for e in self.modifier]) + ']'
        else:
            modifier_str = ''
        if self.entirety and self.entirety.base != '':
            entirety_str = '[of ' + '][of '.join([str(e) for e in self.modifier]) + ']'
        else:
            entirety_str = ''
        return f'{all_str}{modifier_str}{self.base}{entirety_str}'

    def __eq__(self, other):
        if self is None or other is None:
            return False
        return self.base == other.base \
               and self.is_all == other.is_all \
               and self.entirety == other.entirety \
               and len(set(self.modifier)) == len(set(other.modifier)) \
                    == len(set(self.modifier) | set(other.modifier))

    @classmethod
    def str2entity(cls, s: str):
        # *system*
        if s == '*system*':
            for e in Entity.entities:
                if e.base == '':
                    return e
            e = Entity('')
            Entity.entities.append(e)
            return e
        entity = Entity('')
        # 'ALL'
        if s[:3] == 'ALL':
            s = s[4:]
            entity.is_all = True
        # modifiers
        modifier = []
        while s[0] == '[':
            index = s.find(']')
            modifier.append(s[1: index])
            s = s[index+1 :]
        entity.modifier = modifier
        if (index := s.find('[')) > 0:
            entity.base = s[: index]
            entity.entirety = cls.str2entity(s[index+4: -1])
        else:
            entity.base = s
        # if there is already an entity in Entity.entities, use the existing one
        flag = True
        for e in Entity.entities:
            if entity == e:
                entity = e
                flag = False
                break
        if flag:
            Entity.entities.append(entity)
        return entity


def tuples_to_str(t: Union[Req, Condition]) -> str:
    def to_str(l: list) -> str:
        return f'{", ".join([str(i) for i in l])}' if len(l) != 0 else '*void*'
    agent = '*system*' if t.agent.base == '' else str(t.agent)
    elements = [agent, str(t.operation), to_str(t.input), to_str(t.output), to_str(t.restriction)]
    return '(' + ') , ('.join(elements) + ')'


class RequirementError(Exception):
    def __init__(self, reason: str, sentence: str, location: str):
        self.reason = reason
        self.sentence = sentence
        self.location = location
