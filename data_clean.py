######################################################
#
# 1. 数据清洗。语料中Reports属于y，其他的输入属于x。所以观察语料发现如果y为空，那么这段语料中的x也就没有意义了。
#    pandas可以处理这一情况。也需要在预处理时注意这类情况。
#
######################################################

import numpy as np
import pandas as pd
import re
from jieba import posseg
import jieba


REMOVE_WORDS = ['|', '[', ']', '语音', '图片']


def read_stopwords(path):
    lines = set()
    with open(path, mode='r', encoding='utf-8') as f:
        for line in f:
            # Python strip() 方法用于移除字符串头尾指定的字符（默认为空格或换行符）或字符序列。
            # 注意：该方法只能删除开头或是结尾的字符，不能删除中间部分的字符。
            line = line.strip()
            lines.add(line)
    return lines


def remove_words(words_list):
    words_list = [word for word in words_list if word not in REMOVE_WORDS]
    return words_list


# 分词处理
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


# Data解析
def parse_data(train_path, test_path):
    # 读取csv
    train_df = pd.read_csv(train_path, encoding='utf-8')

    # 去除report为空的,即y为空的情况
    # pandas用法强化:inplace如果不为True，那么在最前面需要设定一个变数作为赋值对象
    # Report部分如果为空，则删除此行
    train_df.dropna(subset=['Report'], how='any', inplace=True)

    # 去除x为空的部分，进行填充。剩余字段是输入，包含Brand,Model,Question,Dialogue，如果有空，填充即可
    train_df.fillna('', inplace=True)

    # 实际的输入X仅仅选择两个字段，将其拼接起来
    # cat代表拼接
    train_x = train_df.Question.str.cat(train_df.Dialogue)
    train_y = []
    if 'Report' in train_df.columns:
        train_y = train_df.Report
        assert len(train_x) == len(train_y)

    # 同样的方法处理test语料，这里不需要考虑y为空的情况。即不考虑Report列
    test_df = pd.read_csv(test_path, encoding='utf-8')
    test_df.fillna('', inplace=True)
    test_x = test_df.Question.str.cat(test_df.Dialogue)
    test_y = []
    return train_x, train_y, test_x, test_y


def save_data(data_1, data_2, data_3, data_path_1, data_path_2, data_path_3, stop_words_path):
    stopwords = read_stopwords(stop_words_path)
    with open(data_path_1, 'w', encoding='utf-8') as f1:
        count_1 = 0
        for line in data_1:
            if isinstance(line, str):
                seg_list = segment(line.strip(), cut_type='word')
                seg_list = remove_words(seg_list)
                # 考虑stopwords
                seg_list = [word for word in seg_list if word not in stopwords]
                if len(seg_list) > 0:
                    seg_line = ' '.join(seg_list)
                    f1.write('%s' % seg_line)
                    f1.write('\n')
                    count_1 += 1
        print('train_x_length is ', count_1)

    with open(data_path_2, 'w', encoding='utf-8') as f2:
        count_2 = 0
        for line in data_2:
            if isinstance(line, str):
                seg_list = segment(line.strip(), cut_type='word')
                # seg_list = remove_words(seg_list)
                seg_list = [word for word in seg_list if word not in stopwords]
                if len(seg_list) > 0:
                    seg_line = ' '.join(seg_list)
                    f2.write('%s' % seg_line)
                    f2.write('\n')
                else:
                    f2.write("随时 联系")
                    f2.write('\n')
                    # print('11111')
                count_2 += 1
        print('train_y_length is ', count_2)

    with open(data_path_3, 'w', encoding='utf-8') as f3:
        count_3 = 0
        for line in data_3:
            if isinstance(line, str):
                seg_list = segment(line.strip(), cut_type='word')
                seg_list = remove_words(seg_list)
                seg_list = [word for word in seg_list if word not in stopwords]
                if len(seg_list) > 0:
                    seg_line = ' '.join(seg_list)
                    f3.write('%s' % seg_line)
                    f3.write('\n')
                    count_3 += 1
        print('test_y_length is ', count_3)


def preprocess_sentence(sentence):
    seg_list = segment(sentence.strip(), cut_type='word')
    seg_line = ' '.join(seg_list)
    return seg_line


if __name__ == '__main__':
    train_list_src, train_list_trg, test_list_src, _ = parse_data('../data/AutoMaster_TrainSet.csv',
                                                                  '../data/AutoMaster_TestSet.csv')
    print(len(train_list_src))
    print(len(train_list_trg))
    save_data(train_list_src,
              train_list_trg,
              test_list_src,
              '../data/train_set.seg_x.txt',
              '../data/train_set.seg_y.txt',
              '../data/test_set.seg_x.txt',
              stop_words_path='../data/stop_words.txt')