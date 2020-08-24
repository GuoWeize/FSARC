"""
Configuration file
"""
from typing import Union, Dict, List

from FSARC.Requirement import Req, Condition

# file paths
CoreNLP_path = r'CoreNLP'
dict_yaml = r'dict.yml'
rules_yaml = r'rules.yml'

# type definations
TYPE_NLP   = List[Dict[str, Union[str, int]]]
TYPE_TUPLE = Union[Req, Condition]
