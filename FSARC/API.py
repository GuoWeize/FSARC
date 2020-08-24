# -*- coding: utf-8 -*-
"""
This file provides ConflictDetector with three API method.
!! Please call method 'start' before using APIs and provides the path of CoreNLP directory.

Method 'requirement_model' models Natural Language requirements into tuples.
Method 'requirement_conflict_detect' detects conflicts in Natural Language requirements.
Method 'tuples_conflict_detect' detects conflicts in requirement tuples.
"""
import os
from typing import List

from FSARC.detection import Detector
from FSARC.modelling import model
from FSARC.nlp import start, close
from FSARC.Requirement import Req


class ConflictDetector:
    is_start :bool = False

    @classmethod
    def start(cls):
        start()
        cls.is_start = True

    @classmethod
    def close(cls):
        cls.is_start = False
        close()

    @classmethod
    def requirement_model(cls, req_file: str = None, model_file: str = None, original_req: bool = False) -> None:
        """
        modelling requirements from req_file to tuples, then print to model_file, otherwise print to screen if not given
        :param req_file: path of original requirement file
        :param model_file: path of modelled requirement file
        :param original_req: print the original requirements or not
        """
        cls.check_start()
        if req_file is None:
            req = input()
            if original_req:
                print()
            for s in model(req):
                print(s)
            return
        if not os.path.isfile(req_file):
            print('Invalid file path. Please check the path and call again.')
            return
        print(f'requirements: {req_file} -> modelled requirements: {model_file}')
        with open(req_file, encoding='UTF-8') as fin:
            fout = open(model_file, 'w', encoding='UTF-8') if model_file is not None else None
            for line in fin:
                line = line[: -1] if line[-1] == '\n' else line
                if original_req:
                    print(line, file=fout)
                for req in model(line):
                    print(req, file=fout, end='')
                print('\n', file=fout)
            if fout is not None:
                fout.close()


    @classmethod
    def requirement_conflict_detect(cls, req_file: str, conflict_file: str = None) -> None:
        """
        detecting conflicts in requirements from req_file, then print to model_file, otherwise print to screen if not given
        :param req_file: path of original requirement file
        :param conflict_file: path of conflict file
        """
        cls.check_start()
        if not os.path.isfile(req_file):
            print('Invalid file path. Please check the path and call again.')
            return
        print(f'requirements: {req_file} -> conflicts: {conflict_file}')
        modelled_reqs = []
        count = 1
        with open(req_file, encoding='UTF-8') as fin:
            for line in fin:
                for r in model(line):
                    r.reqid = count
                    count += 1
                    modelled_reqs.append(r)
        cls.conflict_detect(modelled_reqs, conflict_file)


    @classmethod
    def tuples_conflict_detect(cls, model_file: str, conflict_file: str = None) -> None:
        """
        detecting conflicts in requirements from model_file, then print to model_file, otherwise print to screen if not given
        :param model_file: path of modelled requirement file
        :param conflict_file: path of conflict file
        """
        cls.check_start()
        if not os.path.isfile(model_file):
            print('Invalid file path. Please check the path and call again.')
            return
        print(f'modelled requirements: {model_file} -> conflicts: {conflict_file}')
        modelled_reqs = []
        count = 1
        with open(model_file, encoding='UTF-8') as fin:
            for line in fin:
                if len(line) > 10:
                    r = Req.str2Req(line)
                    r.reqid = count
                    count += 1
                    modelled_reqs.append(r)
        cls.conflict_detect(modelled_reqs, conflict_file)


    @classmethod
    def conflict_detect(cls, modelled_reqs: List[Req], conflict_file: str = None):
        conflicts = Detector.detect(modelled_reqs)
        fout = open(conflict_file, 'w', encoding='UTF-8') if conflict_file is not None else None
        for conflict in conflicts:
            print(conflict[0], file=fout)
            for r in conflict[1]:
                print(r, file=fout, end='')
            print(file=fout)
        if fout is not None:
            fout.close()

    @classmethod
    def check_start(cls):
        if not cls.is_start:
            print("CoreNLP not start, please call method 'start' before using")
            raise AssertionError
