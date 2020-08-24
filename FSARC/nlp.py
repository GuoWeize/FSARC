# -*- coding: utf-8 -*-
"""
This file provides interface to using CoreNLP.

Function 'start' should be called before using CoreNLP to initialize it.
Function 'close' should be called after using CoreNLP to shut it down.
Function 'parse' is the interface for CoreNLP parsing.
"""
from typing import Tuple
import json, os, psutil, requests, subprocess, time

from config import CoreNLP_path, TYPE_NLP

process         : subprocess.Popen
url             : str   = ''
class_path_dir  : str   = ''
ROOT_token = {'index': 0,
              'word': '_ROOT_',
              'originalText': '',
              'lemma': '_ROOT_',
              'characterOffsetBegin': -1,
              'characterOffsetEnd': -1,
              'pos': 'ROOT',
              'before': '',
              'after': ''}
props = {'annotators': 'tokenize, pos, lemma, depparse',
         'pipelineLanguage': 'en',
         'outputFormat': 'json'}

def start():
    global class_path_dir, process, url
    # New server
    class_path_dir = os.path.normpath(CoreNLP_path) + os.sep
    port = 9999
    # Start native server
    cmd = "java"
    java_args = "-Xmx8g"
    java_class = "edu.stanford.nlp.pipeline.StanfordCoreNLPServer"
    class_path = f'"{class_path_dir}*"'
    args = [cmd, java_args, '-cp', class_path, java_class, '-port', str(port)]
    args = ' '.join(args)
    with open(os.devnull, 'w') as null_file:
        out_file = null_file
        # Server shell PID is self.p.pid
        process = subprocess.Popen(args, shell=True, stdout=out_file, stderr=subprocess.STDOUT)
    url = 'http://localhost:' + str(port)
    # Wait until server starts
    time.sleep(1)

def close():
    global process, class_path_dir
    try:
        parent = psutil.Process(process.pid)
    except psutil.NoSuchProcess:    # No process
        return
    children = parent.children(recursive=True)
    for p in children:
        p.kill()
    parent.kill()

def parse(text: str) -> Tuple[TYPE_NLP, TYPE_NLP]:
    global url, ROOT_token, props
    text = text.encode('utf-8')
    r = requests.post(url, params={'properties': str(props)}, data=text, headers={'Connection': 'close'})
    result = (json.loads(r.text))['sentences'][0]
    tokens, dependencies = result['tokens'], result['enhancedPlusPlusDependencies']
    # add a special ROOT to tokens to align the index of words
    tokens.insert(0, ROOT_token)
    return tokens, dependencies
