# -*- coding: utf-8 -*-
"""
This file provide functions to help model Natural Language requirements.
"""
import os, yaml
from typing import List, Tuple

from config import dict_yaml, TYPE_NLP
from FSARC.nlp import parse
from FSARC.Requirement import Entity, RequirementError

__all__ = [
    'normalize',
    'NLP_parsing',
    'token2text',
    'find_in_tokens',
    'remove_instances',
    'remove_stopwords',
    'change_ables',
    'find_restrictions',
    'find_op_index',
    'parse_copula',
    'check_op_index',
    'parse_complement',
    'check_not',
    'find_condition_words',
    'parse_passive_agent',
    'parse_active_agent',
    'parse_entity',
    'find_input_output',
    'find_input',
    'common_restriction',
    'frequency_restriction',
    'parse_obj_clause',
    'check_multi_verbs',
]

tokens: TYPE_NLP
dependencies: TYPE_NLP

with open('..' + os.path.sep + dict_yaml, encoding='utf-8') as f:
    dictionary = yaml.load(f.read())
stopwords = dictionary['stop words']
before_instance = dictionary['before instance']
able_words = dictionary['able words']
modal_verbs = dictionary['modal verbs']
condition_leading_words = dictionary['before condition']
before_adj_clause = dictionary['before adj clause']
ignored_type = ['nmod:'+s for s in ['poss', 'of', 'agent', 'by', 'tmod', 'per', 'npmod']]

def normalize(clause: str) -> str:
    index = len(clause) -1
    while clause[index] in ['!', '?', ';', '\n', ' ', '.']:
        index -= 1
    return clause[: index+1] + '.'

def NLP_parsing(text: str):
    global tokens, dependencies
    tokens, dependencies = parse(text)

def token2text(start=1, end=0) -> str:
    if end == 0:
        return ' '.join([t['word'] for t in tokens[start:]])
    return ' '.join([t['word'] for t in tokens[start: end]])

def find_in_tokens(word_list: List[str], start=1, end=0) -> List[int]:
    indexes = []
    search_tokens = tokens[start: end] if end != 0 else tokens[start:]
    for i, token in enumerate(search_tokens):
        if token['lemma'] in word_list:
            indexes.append(i)
    return indexes

def remove_instances(text: str) -> str:
    if (index := text.find(', including:')) > 0 or (index := text.find('including:')) > 0:
        text = text[0: index]
    for phrase in before_instance:
        if (left := text.find(', ' + phrase)) > 0 or (left := text.find(phrase)) > 0:
            if (right := text.find(',', left + 1)) > 0:
                text = text[:left] + text[right + 1: -1]
            else:
                text = text[:left - 1]
    return text

def remove_stopwords(text: str) -> str:
    for words in stopwords:
        text = text.replace(words, '')
    right = 0
    while True:
        left = text.find('(', right + 1)
        right = text.find(')', left + 1)
        if 0 <= left < right:
            text = text.replace(text[left: right + 1], '')
        else:
            return text

def change_ables(text: str) -> str:
    text = text.replace('shall be able to', 'can')
    text = text.replace('be able to ', '')
    if text.find('provide ') >= 0:
        for item in able_words:
            text = text.replace('shall ' + item, 'can ')
            text = text.replace(item, '')
    return text

def find_restrictions(text: str) -> Tuple[str, List[str]]:
    restrictions = []
    for w in dictionary['before restriction']:
        if (l_index := text.find(w)) >= 0:
            right = text.find(',', l_index)
            res = text[l_index: right].replace('.', '')
            if res != '':
                restrictions.append(res)
            text = text[:l_index] + text[right:-1]
    return text, restrictions

def find_op_index(is_req: bool) -> Tuple[int, bool, bool]:
    # some condition clause omit the subject
    if tokens[1]['pos'] == 'VBN' and tokens[1]['lemma'] != 'be':
        return 1, True, False
    if tokens[1]['pos'] == 'VBG':
        return 1, False, False
    if is_req:  # Requirement
        # the word after modal verbs is recognized as verb
        for i, token in enumerate(tokens[:-1]):
            if token['lemma'] in modal_verbs:
                if tokens[i + 1]['lemma'] == 'be':
                    return i + 2, False, token['lemma'] in ['can', 'may']
                else:
                    return i + 1, False, token['lemma'] in ['can', 'may']
    else:  # Condition & Object Clause
        # the word that ROOT point to is recognized as verb
        return dependencies[0]['dependent'], False, False
    return 0, False, False

def parse_copula(op_index: int) -> Tuple[int, str]:
    for d in dependencies:
        if d['governor'] == op_index and d['dep'] == 'cop' and tokens[d['dependent']]['lemma'] == 'be':
            be_index = d['dependent']
            copula_index = d['governor']
            predicate = token2text(be_index, copula_index+1)
            new_clause = token2text(end=be_index) + ' do ' + token2text(start=copula_index+1)
            NLP_parsing(new_clause)
            return be_index,predicate
    return op_index, ''

def check_op_index(op_index: int, is_passive: bool) -> Tuple[int, bool, str]:
    # if CoreNLP cannot mark the predicate as a verb, recognize the word follows "shall" as verb
    if op_index == 0:
        indexes = find_in_tokens(modal_verbs)
        if len(indexes) > 0:
            op_index = indexes[0] + 1
    if op_index == 0:
        raise RequirementError(
            'cannot find correct operation word in this sentence',
            token2text(),
            'modelling -> parse_operation'
        )
    # check up passive voice
    if tokens[op_index - 1]['lemma'] == 'be' and tokens[op_index]['pos'] == 'VBN':
        is_passive = True
    return op_index, is_passive, tokens[op_index]['lemma']

def parse_complement(op_index) -> str:
    complements = ''
    for d in [dep for dep in dependencies if dep['governor'] == op_index and dep['dep'] == 'xcomp']:
        complement_index = d['dependent']
        to_indexes = find_in_tokens(['to'], op_index+1, complement_index)
        if len(to_indexes) > 0:
            if tokens[complement_index]['lemma'] == tokens[complement_index]['word']:
                complements += (' to ' + token2text(op_index+1, complement_index))
            else:
                complements += (' to be ' + token2text(op_index + 1, complement_index))
        else:
            complements += (' ' + token2text(op_index+1, complement_index))
    return complements

def check_not(op_index: int) -> bool:
    for d in dependencies:
        if d['governor'] == op_index and d['dep'] == 'neg':
            return True
    return False

def find_condition_words():
    return find_in_tokens(condition_leading_words)

def parse_passive_agent(op_index: int) -> Tuple[int, int]:
    agent_index, input_output_index = -1, -1
    # find formal subject
    for dep in dependencies:
        if dep['governor'] == op_index and dep['dep'] == 'nsubjpass':
            input_output_index = dep['dependent']
            break
    # find real subject
    for dep in dependencies:
        if dep['dep'] == 'case' and dep['dependentGloss'] == 'by':
            agent_index = dep['governor']
            break
    return agent_index, input_output_index

def parse_active_agent(op_index: int) -> int:
    for dep in dependencies:
        if dep['governor'] == op_index and dep['dep'][:5] == 'nsubj':
            return dep['dependent']
    # copula structure
    for dep in dependencies:
        if dep['dep'][:5] == 'nsubj':
            return dep['dependent']
    # CoreNLP can not identity the subject
    if tokens[dependencies[0]['dependent']]['pos'] == 'NN':
        return dependencies[0]['dependent']

def parse_entity(entity_index: int) -> Entity:
    compound = ''
    for dep in dependencies:
        if dep['governor'] == entity_index and dep['dep'] == 'compound':
            word = dep['dependentGloss'].lower() if dep['dependentGloss'][-1] == 'S' else tokens[dep['dependent']]['lemma'].lower()
            compound = word if compound == '' else compound + ' ' + word
    if compound != '':
        compound += ' '

    temp = tokens[entity_index]
    word = temp['word'].lower() if temp['word'][-1] == 'S' else temp['lemma'].lower()

    base = compound + word
    entity = Entity(base)       # entity to return

    for dependency in dependencies:
        if dependency['governor'] != entity_index:
            continue
        if dependency['dep'] == 'det' and dependency['dependentGloss'].upper() in ['ALL', 'EACH']:
            entity.is_all = True
        elif dependency['dep'] in ['nummod', 'amod']:
            if tokens[dependency['dependent'] - 1]['pos'] == 'CD':
                mod = ''
                for dep in [dep for dep in dependencies if
                            dep['dep'] == 'advmod' and dep['governor'] == dependency['dependent']]:
                    for token in tokens[dep['dependent'] - 1: dep['governor'] - 1]:
                        mod += token['lemma'] + ' '
                entity.modifier.append(mod + dependency['dependentGloss'])
            else:
                entity.modifier.append(dependency['dependentGloss'])
        elif dependency['dep'] in ['nmod:poss', 'nmod:of']:
            entirety = parse_entity(dependency['dependent'])
            entity.entirety = entirety
            entirety.parts.append(entity)
        elif dependency['dep'] in ['acl', 'acl:relcl']:
            governor = dependency['governor']
            dependent = dependency['dependent']
            clause = parse_adj_clause(entity_index, governor, dependent)
            entity.modifier.append(clause)
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

def parse_adj_clause(obj_index: int, governor: int, dependent: int) -> str:
    adj_clause = ''
    begin, end = 0, len(tokens)
    for i, token in enumerate(tokens[governor + 1: dependent]):
        if token['lemma'] in before_adj_clause:
            begin = i
            for dep in dependencies:
                if dep['dep'] == 'case' and dep['governor'] == i:
                    begin = i - 1
                    break
            break
    if begin == 0:
        begin = obj_index + 1
    for i, token in enumerate(tokens[dependent + 1:]):
        if token['lemma'] in ['.', ',', 'and', 'or']:
            end = i
            break
    for token in tokens[begin: end - 1]:
        adj_clause += token['word'] + ' '
    adj_clause += tokens[end - 1]['word']
    return adj_clause

def find_input_output(op_index: int) -> Tuple[List[Entity], List[Entity]]:
    inputs, outputs = [], []
    for dep in dependencies:
        if dep['governor'] == op_index and dep['dep'] == 'dobj':
            o = parse_entity(dep['dependent'])
            if o not in inputs:
                inputs.append(o)
            if o not in outputs:
                outputs.append(o)
    return inputs, outputs

def find_input() -> List[Entity]:
    inputs = []
    for dep in dependencies:
        if dep['dep'][:4] == 'nmod':
            if dep['dep'] in ignored_type:
                pass
            elif dep['dep'] == 'nmod:at' and dep['dependentGloss'] == 'time':
                pass
            elif (o := parse_entity(dep['dependent'])) not in inputs:
                inputs.append(o)
        if dep['dep'] in ['nummod', 'compound']:
            if (o := parse_entity(dep['governor'])) not in inputs:
                inputs.append(o)
    return inputs

def common_restriction():
    restriction = []
    for dep in dependencies:
        if dep['dep'] == 'advmod' and dep['dependentGloss'].lower() not in ['when', 'then']:
            restriction.append(dep['dependentGloss'].lower())
    for dep in [dep for dep in dependencies if dep['dep'][:4] == 'nmod']:
        end_index = dep['dependent']
        if tokens[end_index]['pos'] == 'NNP' or tokens[end_index]['lemma'] == 'time':
            for d in [d for d in dependencies if d['dep'] == 'case' and d['governor'] == end_index]:
                restriction.append(token2text(d['dependent'], end_index + 1))
                break
    return restriction

def frequency_restriction():
    restriction = []
    # every time
    for dep in [dep for dep in dependencies if dep['dep'] == 'nmod:tmod']:
        end_index = dep['dependent']
        for d in dependencies:
            if d['dep'] == 'det' and d['governor'] == end_index and d['dependentGloss'] == 'every':
                restriction.append(token2text(d['dependent'], end_index + 1))
                break
    # 'everyday'
    for t in tokens:
        if t['lemma'] == 'everyday':
            restriction.append('everyday')
    # N time1 per/a time2
    for dep in [dep for dep in dependencies if dep['dep'] == 'nmod:per' or dep['dep'] == 'nmod:npmod']:
        time1 = dep['governor']
        time2 = dep['dependent']
        for d in [d for d in dependencies if d['dep'] == 'nummod' and d['governor'] == time1]:
            restriction.append(token2text(d['dependent'], time2 + 1))
            break
    return restriction

def parse_obj_clause(op_index: int) -> str:
    flag = False
    obj_clause = ''
    for dep in dependencies:
        if dep['governor'] == op_index and dep['dep'] == 'ccomp':
            index = dep['dependent']
            for d in dependencies:
                if d['governor'] == index and d['dep'] == 'mark':
                    flag = True
                    for i, token in enumerate(tokens):
                        if i == op_index + 1 and token['lemma'] != 'that':
                            obj_clause += token['word'] + ' '
                        elif i > op_index + 1:
                            obj_clause += token['word'] + ' '
                    break
            if flag:
                break
    return obj_clause


def check_multi_verbs(op_index: int, passive: bool) -> Tuple[bool, str, str]:
    for dep in dependencies:
        if dep['governor'] == op_index and dep['dependentGloss'] in ['and', 'or']:
            and_index = dep['dependent']
            obj_index = None  # word index of the object
            mutual_obj = True  # whether this two verb has mutual object
            # try to find object after the 2nd verb
            for i, token in enumerate(tokens[and_index:]):
                if token['pos'][0] == 'N' or token['pos'] in ['DT', 'JJ']:
                    obj_index = i
                    break
            # if can not find the object, certainly not have mutaul object
            if obj_index is None:
                mutual_obj = False
            # if find the mutaul object, try to find an object after the 1st verb,
            # if also find it, certainly not have mutaul object
            else:
                for token in tokens[op_index: and_index]:
                    if token['pos'][0] == 'N' or token['word'] == 'be':
                        mutual_obj = False
                        break
            # split the sentence
            start_part = token2text(end=op_index)
            end_part = token2text(start=obj_index)
            op1 = tokens[op_index]['word'] + ' ' if passive else tokens[op_index]['lemma']
            op2 = tokens[and_index + 1]['word'] + ' ' if passive else tokens[and_index + 1]['lemma']
            obj1 = token2text(op_index + 1, and_index)
            obj2 = token2text(and_index + 1, obj_index)
            clause_1 = ' '.join([start_part, op1, obj1, end_part])
            if mutual_obj:
                clause_2 = ' '.join([start_part, op2, obj1, end_part])
            else:
                clause_2 = ' '.join([start_part, op2, obj2, end_part])
            return True, clause_1, clause_2

    return False, '', ''
