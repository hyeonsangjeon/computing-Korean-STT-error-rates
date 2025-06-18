from __future__ import unicode_literals
import logging
from typing import Any, Dict, List, Tuple, Union
import sys
import pandas as pd
import jiwer
import json
from collections import OrderedDict
import re


# -*- coding: utf-8 -*-

def levenshtein(u, v):
    prev = None
    curr = [0] + list(range(1, len(v) + 1))
    # Operations: (SUB, DEL, INS)
    prev_ops = None
    curr_ops = [(0, 0, i) for i in range(len(v) + 1)]
    for x in range(1, len(u) + 1):
        prev, curr = curr, [x] + ([None] * len(v))
        prev_ops, curr_ops = curr_ops, [(0, x, 0)] + ([None] * len(v))
        for y in range(1, len(v) + 1):
            delcost = prev[y] + 1
            addcost = curr[y - 1] + 1
            subcost = prev[y - 1] + int(u[x - 1] != v[y - 1])
            curr[y] = min(subcost, delcost, addcost)
            if curr[y] == subcost:
                (n_s, n_d, n_i) = prev_ops[y - 1]
                curr_ops[y] = (n_s + int(u[x - 1] != v[y - 1]), n_d, n_i)
            elif curr[y] == delcost:
                (n_s, n_d, n_i) = prev_ops[y]
                curr_ops[y] = (n_s, n_d + 1, n_i)
            else:
                (n_s, n_d, n_i) = curr_ops[y - 1]
                curr_ops[y] = (n_s, n_d, n_i + 1)
    return curr[len(v)], curr_ops[len(v)]


def get_unicode_code(text):
    result = ''.join(char if ord(char) < 128 else '\\u' + format(ord(char), 'x') for char in text)
    return result


def _measure_cer(
        reference: str, transcription: str
) -> Tuple[int, int, int, int]:
    """
    소스 단어를 대상 단아로 변환하는 데 필요한 편집 작업(삭제, 삽입, 바꾸기)의 수를 확인합니다.
    hints 횟수는 소스 딘아의 전체 길이에서 삭제 및 대체 횟수를 빼서 제공할 수 있습니다.

    :param transcription: 대상 단어로 변환할 소스 문자열
    :param reference: 소스 단어
    :return: a tuple of #hits, #substitutions, #deletions, #insertions
    """

    ref, hyp = [], []

    ref.append(reference)
    hyp.append(transcription)

    cer_s, cer_i, cer_d, cer_n = 0, 0, 0, 0
    sen_err = 0

    for n in range(len(ref)):
        # update CER statistics
        _, (s, i, d) = levenshtein(hyp[n], ref[n])
        cer_s += s
        cer_i += i
        cer_d += d
        cer_n += len(ref[n])

        # update SER statistics
        if s + i + d > 0:
            sen_err += 1

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    hits = len(reference) - (substitutions + deletions)  # correct characters

    return hits, substitutions, deletions, insertions


def _measure_wer(
        reference: str, transcription: str
) -> Tuple[int, int, int, int]:
    """
    소스 문자열을 대상 문자열로 변환하는 데 필요한 편집 작업(삭제, 삽입, 바꾸기)의 수를 확인합니다.
    hints 횟수는 소스 문자열의 전체 길이에서 삭제 및 대체 횟수를 빼서 제공할 수 있습니다.

    :param transcription: 대상 단어
    :param reference: 소스 단어
    :return: a tuple of #hits, #substitutions, #deletions, #insertions
    """

    ref, hyp = [], []

    ref.append(reference)
    hyp.append(transcription)

    wer_s, wer_i, wer_d, wer_n = 0, 0, 0, 0
    sen_err = 0

    for n in range(len(ref)):
        # update WER statistics
        _, (s, i, d) = levenshtein(hyp[n].split(), ref[n].split())
        wer_s += s
        wer_i += i
        wer_d += d
        wer_n += len(ref[n].split())
        # update SER statistics
        if s + i + d > 0:
            sen_err += 1

    substitutions = wer_s
    deletions = wer_d
    insertions = wer_i
    hits = len(reference.split()) - (substitutions + deletions)  # correct words between refs and trans

    return hits, substitutions, deletions, insertions


def _measure_er(
        reference: str, transcription: str
) -> Tuple[int, int]:
    """
    완벽하게 변역한 문장여부를 판단합니다.
    :param transcription: 대상 단어로 변환할 소스 문자열
    :param reference: 소스 단어
    :return: Boolean
    """
    TBD1 = ""
    TBD2 = ""
    return TBD1, TBD2


def get_cer(reference, transcription, rm_punctuation=True) -> json:
    # 문자 오류율(CER)은 자동 음성 인식 시스템의 성능에 대한 일반적인 메트릭입니다.
    # CER은 WER(단어 오류율)과 유사하지만 단어 대신 문자에 대해 작동합니다.
    # 이 코드에서는 문제는 사람들이 띄어쓰기를 지키지 않고 작성한 텍스트를 컴퓨터가 정확하게 인식하는 것이 매우 어렵기 때문에 인식에러에서 생략합니다.
    # CER의 출력은 특히 삽입 수가 많은 경우 항상 0과 1 사이의 숫자가 아닙니다. 이 값은 종종 잘못 예측된 문자의 백분율과 연관됩니다. 값이 낮을수록 좋습니다.
    # CER이 0인 ASR 시스템의 성능은 완벽한 점수입니다.

    # CER = (S + D + I) / N = (S + D + I) / (S + D + C)
    # S is the number of the substitutions,
    # D is the number of the deletions,
    # I is the number of the insertions,
    # C is the number of the correct characters,
    # N is the number of the characters in the reference (N=S+D+C).

    refs = jiwer.RemoveWhiteSpace(replace_by_space=False)(reference)
    trans = jiwer.RemoveWhiteSpace(replace_by_space=False)(transcription)

    if rm_punctuation == True:
        refs = jiwer.RemovePunctuation()(refs)
        trans = jiwer.RemovePunctuation()(trans)
    else:
        refs = reference
        trans = transcription

    [hits, cer_s, cer_d, cer_i] = _measure_cer(refs, trans)

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    incorrect = substitutions + deletions + insertions
    total = substitutions + deletions + hits + insertions

    cer = incorrect / total

    result = OrderedDict()
    result = {'cer': cer, 'substitutions': substitutions, 'deletions': deletions, 'insertions': insertions}
    # print('cer : ',100.0*cer,'%') #normalized

    return result


def get_wer(reference, transcription, rm_punctuation=True) -> json:
    # WER = (S + D + I) / N = (S + D + I) / (S + D + C)
    # S is the number of the substitutions,
    # D is the number of the deletions,
    # I is the number of the insertions,
    # C is the number of the correct words,
    # N is the number of the words in the reference (N=S+D+C).
    if rm_punctuation == True:
        refs = jiwer.RemovePunctuation()(reference)
        trans = jiwer.RemovePunctuation()(transcription)
    else:
        refs = reference
        trans = transcription
    [hits, wer_s, wer_d, wer_i] = _measure_wer(refs, trans)

    substitutions = wer_s
    deletions = wer_d
    insertions = wer_i

    incorrect = substitutions + deletions + insertions
    total = substitutions + deletions + hits + insertions

    wer = incorrect / total
    result = OrderedDict()
    result = {'wer': wer, 'substitutions': substitutions, 'deletions': deletions, 'insertions': insertions}

    return result


def get_crr(reference, transcription, rm_punctuation=True) -> json:
    """
    1 - CER 으로, Character의 error율이 아닌 정답률을 계산
    :param transcription: 대상 단어로 변환할 소스 문자열
    :param reference: 소스 단어
    :return: Boolean
    """
    refs = jiwer.RemoveWhiteSpace(replace_by_space=False)(reference)
    trans = jiwer.RemoveWhiteSpace(replace_by_space=False)(transcription)

    if rm_punctuation == True:
        refs = jiwer.RemovePunctuation()(refs)
        trans = jiwer.RemovePunctuation()(trans)
    else:
        refs = reference
        trans = transcription

    [hits, cer_s, cer_d, cer_i] = _measure_cer(refs, trans)

    substitutions = cer_s
    deletions = cer_d
    insertions = cer_i
    incorrect = substitutions + deletions + insertions
    total = substitutions + deletions + hits + insertions

    crr = round(1 - (incorrect / total), 2)

    result = OrderedDict()
    result = {'crr': crr, 'substitutions': substitutions, 'deletions': deletions, 'insertions': insertions}
    return result


COMPLEX_JOSA = [
    # 단일 조사
    "의", "에", "에서", "도", "만", "를", "을", "이", "가", "과", "와", "으로", "로", "부터",
    "까지", "에게", "께", "한테", "밖에", "마저", "이나", "나", "며", "든지", "라도", "조차",
    # 복합/결합 조사
    "에서부터", "에게서", "으로부터", "까지도", "밖에도", "이라도", "이나마", "라도나", "와도", "도만", "까지도", "에도",
    "이나마", "라도나", "조차도", "치고는"
]
COMPLEX_EOMI = [
    "다", "니다", "합니다", "했다", "하고", "하는데", "했었다", "한다면", "한다니까", "하니", "하더니", "하여도", "하더라도", "했었지", "하려면"
]

def make_keyword_pattern(keyword, josa_list, eomi_list=None):
    """
    주어진 키워드와 조사, 어미 리스트를 기반으로 정규 표현식 패턴을 생성합니다.
    Args:
        keyword (str): 키워드 문자열
        josa_list (list of str): 조사 리스트
        eomi_list (list of str, optional): 어미 리스트
    Returns:
        re.Pattern: 생성된 정규 표현식 패턴
    1. 키워드의 각 글자 사이에 optional space (\s*)를 허용합니다.
    2. 조사 리스트를 |로 연결하여 조사 패턴을 만듭니다.
    3. 어미 리스트가 있을 경우, 어미 패턴도 생성하여 조사 패턴과 함께 붙입니다.
    4. 최종적으로 키워드 + 조사/어미 패턴을 정규 표현식으로 컴파일합니다.
    5. 예시: "삼성전자" 키워드와 ["의", "에서", "와"] 조사 리스트, ["다", "합니다"] 어미 리스트가 주어질 경우,
       정규 표현식은 다음과 같이 생성됩니다:
       r"\s*삼\s*성\s*전\s*자(\s*(의|에서|와)(다|합니다)?)?"
       이 패턴은 "삼성전자", "삼성전자에서", "삼성전자와 다" 등 다양한 형태의 키워드 매칭을 허용합니다.
    """
    # 키워드의 각 글자 사이에 optional space (\s*) 허용
    keyword_pattern = r'\s*'.join(list(keyword))
    # 조사 패턴 (|로 연결)
    josa_pattern = '|'.join(sorted(josa_list, key=lambda x: -len(x)))
    # 어미 패턴도 있을 경우 같이 붙임
    if eomi_list:
        eomi_pattern = '|'.join(sorted(eomi_list, key=lambda x: -len(x)))
        # 조사, 어미 중 하나 이상 붙을 수 있게
        full_pattern = rf"{keyword_pattern}({josa_pattern}|{eomi_pattern})?"
    else:
        full_pattern = rf"{keyword_pattern}({josa_pattern})?"
    return re.compile(full_pattern)



def calculate_keyword_error_rate_with_pattern(reference_sentences, hypothesis_sentences, keywords, josa_list, eomi_list=None):
    """
    각 키워드별로 등장한 횟수와 오류 횟수를 집계하고, 정확도와 에러율을 계산합니다.
    전체 키워드 통계도 함께 제공합니다.

    Args:
        reference_sentences (list of str): 정답 문장 리스트
        hypothesis_sentences (list of str): STT 결과 문장 리스트
        keywords (list of str): 추적할 키워드 리스트
        josa_list (list of str): 조사 리스트
        eomi_list (list of str, optional): 어미 리스트

    Returns:
        dict: {
            "keywords": {키워드: {"total": 등장횟수, "correct": 정확개수, "errors": 오류횟수, "accuracy": 정확도율, "error_rate": 에러율}},
            "summary": {"total_keywords": 전체등장횟수, "correct_keywords": 전체정확횟수, "incorrect_keywords": 전체오류횟수, "keyword_error_rate": 전체에러율}
        } 형태의 딕셔너리
    """
    result = {kw: {"total": 0, "correct": 0, "errors": 0, "accuracy": 0.0, "error_rate": 0.0} for kw in keywords}
    patterns = {kw: make_keyword_pattern(kw, josa_list, eomi_list) for kw in keywords}

    for ref, hyp in zip(reference_sentences, hypothesis_sentences):
        for kw, pattern in patterns.items():
            if pattern.search(ref):
                result[kw]["total"] += 1
                if pattern.search(hyp):
                    result[kw]["correct"] += 1
                else:
                    result[kw]["errors"] += 1
    
    # 개별 키워드 정확도와 에러율 계산
    for kw in keywords:
        if result[kw]["total"] > 0:
            result[kw]["accuracy"] = round(result[kw]["correct"] / result[kw]["total"], 4)
            result[kw]["error_rate"] = round(result[kw]["errors"] / result[kw]["total"], 4)
        else:
            result[kw]["accuracy"] = 0.0
            result[kw]["error_rate"] = 0.0
    
    # 전체 통계 계산
    total_keywords = sum(kw_stats["total"] for kw_stats in result.values())
    correct_keywords = sum(kw_stats["correct"] for kw_stats in result.values())
    incorrect_keywords = sum(kw_stats["errors"] for kw_stats in result.values())
    keyword_error_rate = round(incorrect_keywords / total_keywords, 4) if total_keywords > 0 else 0.0
    
    # 결과 구조화
    final_result = {
        "keywords": result,
        "summary": {
            "total_keywords": total_keywords,
            "correct_keywords": correct_keywords,
            "incorrect_keywords": incorrect_keywords,
            "keyword_error_rate": keyword_error_rate
        }
    }
    
    return final_result