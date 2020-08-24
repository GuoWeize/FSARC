# -*- coding: utf-8 -*-
"""
This file provides interface to model Natural Language requirements.

Function 'model' is the interface for requirements modelling.
"""
import copy
from typing import List, Tuple

from config import TYPE_TUPLE
from FSARC.patterns import *
from FSARC.Requirement import Req, Entity, Condition, RequirementError

__all__ = ['model']

req_count   : int = 1
group_count : int = 1

def model(text: str, mode: str = 'req') -> List[TYPE_TUPLE]:
    global req_count, group_count
    requirement_result = []
    conditions_list = []
    restrictions = []

    text = normalize(text)
    if mode == 'req':
        text, restrictions = preprocess(text)

    NLP_parsing(text)

    if mode == 'req':
        main_clause, conditions_list = find_conditions()
        tuples = Req(req_count)
        req_count += 1
        NLP_parsing(main_clause)
    elif mode == 'verbs':
        tuples = Req(req_count)
        req_count += 1
        tuples.groupid = group_count
    elif mode == 'condition':
        tuples = Condition()
    else:
        raise AttributeError

    op_index, passive = parse_operation(tuples)
    # object clause
    if mode == 'req':
        obj_clause = parse_obj_clause(op_index)
        if obj_clause != '':
            NLP_parsing(obj_clause)
            op_index, passive = parse_operation(tuples)
    # multiple verbs
    has_multi, sentence_1, sentence_2 = check_multi_verbs(op_index, passive)
    # not has multiple verbs
    if not has_multi:
        parse_agent(tuples, op_index, passive)
        inputs, outputs = parse_input_output(op_index)
        tuples.input += inputs
        tuples.output += outputs
        tuples.restriction = parse_restriction()
        if mode != 'req':
            return [tuples]
        tuples.restriction.extend(restrictions)
        if len(conditions_list) == 0:
            requirement_result.append(tuples)
        for conditions in conditions_list:
            event = []
            for condition in conditions:
                c_tuple_list = model(condition, 'condition')
                for c_tuple in c_tuple_list:
                    event.append(c_tuple)
            tuples.event = event
            replace_agent(tuples)      # change entities of omiited subject in passive condition clause
            new_req = copy.deepcopy(tuples)
            requirement_result.append(new_req)
        return requirement_result
    # has multiple verbs, only requirement may have multiple verbs
    if has_multi:
        req_count -= 1
        group_count += 1
        r1 = model(sentence_1, 'verbs')[0]
        r2 = model(sentence_2, 'verbs')[0]
        for res in restrictions:
            r1.restriction.append(res)
            r2.restriction.append(res)
        for conditions in conditions_list:
            event = []
            for condition in conditions:
                c_tuple_list = model(condition, 'condition')
                for c_tuple in c_tuple_list:
                    event.append(c_tuple)
            r1.event = event
            r2.event = event
            replace_agent(r1)  # change entities of omiited subject in passive condition clause
            replace_agent(r2)
            requirement_result.append(r1)
            requirement_result.append(r2)
        return requirement_result

def preprocess(text: str) -> Tuple[str, List[str]]:
    text = remove_stopwords(text)
    text = remove_instances(text)
    text = change_ables(text)
    return find_restrictions(text)

########################################## identify tuples ###########################################
def parse_operation(tuples: TYPE_TUPLE) -> Tuple[int, bool]:
    # op_index: the word index of the predicate
    # is_passive: whether the sentence is passive voice
    op_index, is_passive, tuples.operation.Able = find_op_index(type(tuples) == Req)
    # check up copula structure, and change it to the verb 'do' for parsing
    op_index, predicate = parse_copula(op_index)
    if predicate != '':
        tuples.operation.predicate = predicate
    # check up op_index and is_passive again
    op_index, is_passive, predicate = check_op_index(op_index, is_passive)
    # update tuples' operation
    if tuples.operation.predicate == '':
        tuples.operation.predicate = predicate
    # parse open complement (including to do)
    complements = parse_complement(op_index)
    if len(complements) > 0:
        tuples.operation.predicate += complements
    # check up NOT
    tuples.operation.Not = check_not(op_index)
    return op_index, is_passive

def parse_agent(tuples: TYPE_TUPLE, op_index: int, passive: bool) -> int:
    if passive:
        agent_index, input_output_index = parse_passive_agent(op_index)
        if input_output_index != -1:
            entity = parse_entity(input_output_index)
            tuples.input.append(entity)
            tuples.output.append(entity)
        if agent_index == -1:
            if type(tuples) == Condition:
                # the formal subject of the condition, namely agent of main clause, is omitted.
                # it should be input and output of the condition
                tuples.input.append(Entity('*'))
                tuples.output.append(Entity('*'))
            else:
                raise RequirementError('The subject of the clause is missing.',
                                       token2text(),
                                       'modelling.py -> _agent')
    else:   # active voice
        agent_index = parse_active_agent(op_index)
    tuples.agent = parse_entity(agent_index)
    return agent_index

def parse_input_output(op_index: int) -> Tuple[List[Entity], List[Entity]]:
    inputs, outputs = find_input_output(op_index)
    inputs.extend(find_input())
    return inputs, outputs

def parse_restriction() -> List[str]:
    restriction = common_restriction()
    restriction.extend(frequency_restriction())
    if len(restriction) == 1 and restriction[0] == '':
        restriction = []
    return restriction

########################################### other functions ###########################################
def find_conditions() -> Tuple[str, List[str]]:
    # find condition leading words
    words_indexes = find_condition_words()
    # find punctuations after condition leading words
    ranges = []
    for words_index in words_indexes:
        punc_index = find_in_tokens([',', '.'], words_index)
        if len(punc_index) > 0:
            ranges.append((words_index, punc_index[0]))
        else:
            raise RequirementError(
                'there is no punctuation after the condition leading words',
                token2text(),
                'modelling -> find_conditions'
            )
    conditions = [token2text(start, end) for start, end in ranges]
    main_clause = token2text()
    for condition in conditions:
        main_clause.replace(condition, '')
    main_clause.replace(',', '')
    main_clause.replace('  ', ' ')
    return main_clause, conditions

def replace_agent(req: Req) -> None:
    for condition in req.event:
        condition.input =  [req.agent if entity.base == '*' else entity for entity in condition.input]
        condition.output = [req.agent if entity.base == '*' else entity for entity in condition.output]

def replace_content(restriction: List[str], contents: List[str]) -> List[str]:
    new_restriction = []
    for content in contents:
        new_content = f'"{content}"'
        new_restriction = [r.replace(content, new_content) for r in restriction]
    return new_restriction
