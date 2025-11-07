##################################################
#
# 1. 分词
# 2. 词向量训练，增加数据训练
#
#
##################################################

import numpy as np
import pandas as pd
import re
from jieba import posseg
import jieba


def segment(sentence, cut_type='word', pos=False):
    if pos:
        if cut_type == 'word':
            word_pos_seq = posseg.lcut(sentence)
            word_seq, pos_seq = [], []
            for w, p in word_pos_seq:
                word_seq.append(w)
                pos_seq.append(p)
            return word_seq, pos_seq
        elif cut_type == 'char':
            word_seq = list(sentence)
            pos_seq = []
            for w in word_seq:
                w_p = posseg.lcut(w)
                pos_seq.append(w_p[0].flag)
            return word_seq, pos_seq
    else:
        if cut_type == 'word':
            return jieba.lcut(sentence)
        elif cut_type == 'char':
            return list(sentence)


print(segment('我比较喜欢成都的生活', 'word'))
print(segment('我比较喜欢成都的生活', 'char'))
print(segment('我比较喜欢成都的生活', 'word', True))
print(segment('我比较喜欢成都的生活', 'char', True))


import jieba
import os
import time
import gensim
from gensim.models import Word2Vec
import warnings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
from gensim.models.word2vec import LineSentence


# Cutting words and saving to corpus file
def write_token_to_file(infile, outfile):
    words = []
    for line in open(infile, 'r', encoding='utf-8'):
        line = line.strip()
        if line:
            w = jieba.lcut(line)
            words += w + ['\n']
    outfile.writelines(' '.join(words))


def train_w2v_model(path):
    start_time = time.time()
    # workers:线程, size:词向量维度,min_count:过滤低频词,max_vocab_size:控制词表的长度
    # 用LineSentence做训练，训练文本必须为分词之后的数据。
    w2v_model = Word2Vec(LineSentence(path), workers=4, size=50, min_count=1)  # Using 4 threads min_count = 5
    w2v_model.save('w2v.model')  # Can be used for continue training
    # 如上，还有一种保存方式。速度更快也够便捷，但是无法后期维护和改善。
    # w2v_model.wv.save('w2v.model') # Smaller and faster but can't be trained later
    print('training time:', time.time() - start_time)


def get_model_from_file():
    model = Word2Vec.load('w2v.model')
    return model


if __name__ == '__main__':
    path1 = './data/small_corpus.txt'
    train_w2v_model(path1)
    model = Word2Vec.load('./w2v.model')
    print(model.most_similar('车'))
    # 以上为模拟Baseline构成。接下来回增加语料。
    with open('./data/sentences.txt', 'r', encoding='utf-8') as f:
        data = f.readlines()
        f.close()
    new_words = []
    for line in data:
        line = line.strip().split(' ')
        new_words.append(line)
    # epochs:训练几个循环。total_examples:重要参数，代表到底有多少个样本
    model.train(sentences=new_words, epochs=1, total_examples=len(new_words))
    # # model.save('w2v_add.model')
    # model1 = Word2Vec.load('./w2v_add.model')
    print(model.most_similar('车'))
    print(model['的基督教基督教'])

