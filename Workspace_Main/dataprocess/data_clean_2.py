# -*- coding: utf-8 -*-
import re
from Workspace_Main.utils.config import *
import pandas as pd
import jieba


def data_load(raw_data_path, content):
    # data loading
    train_df = pd.read_csv(raw_data_path, encoding='utf-8')

    # 去除report为空的,即y为空的情况
    # pandas用法强化:inplace如果不为True，那么在最前面需要设定一个变数作为赋值对象
    # Report部分如果为空，则删除此行
    if content == 'train':
        train_df.dropna(subset=['Report'], how='any', inplace=True)

    # fill null cell
    return train_df.fillna('')


def text_sort_out(text):
    r1 = re.compile(r'\[.*?\]')
    r2 = re.compile(r'\|(车主说：)|\|(技师说：)|(技师说：)|(车主说：)')
    r3 = re.compile(u"[^a-zA-Z0-9\u4e00-\u9fa5]")
    tmp = r1.sub(' ', text)
    tmp = r2.sub(' ', tmp)
    res = r3.sub(' ', tmp)
    return res


def tokens_jieba(txt):
    from collections import Counter
    seg_list = jieba.cut(txt)
    c = Counter()
    for x in seg_list:
        if len(x) > 1 and x != '\r\n':
            c[x] += 1
    print('常用词频度统计结果')
    for (k, v) in c.most_common(DICT_INDEX):
        print('%s%s  %d' % ('  ' * (5 - len(k)), k, v))


def frame2text(*data):
    columns = ['Question', 'Dialogue', 'Report']  # ['QID', 'Brand', 'Model', 'Question', 'Dialogue', 'Report']
    text = ''
    res = ''
    # read multiple dataframes
    for df in data:
        target = []
        # append target columns
        for item in columns:
            if item in df.columns:
                target.append(item)
        print(target)
        # save text as a string
        # TODO: learn DataFrame's apply function https://blog.csdn.net/yanjiangdi/article/details/94764562
        text += '\n'.join(df[target].apply(lambda x: ' '.join(x), axis=1))
        res = text_sort_out(text)
    # print(len(text))
    # print(len(res))
    return res


if __name__ == '__main__':
    '''
    数据预处理
    1. 词向量训练预处理
    '''

    # load raw data from .csv
    data_train = data_load(RAW_DATA_TRAIN_TEST, 'train')
    data_valid = data_load(RAW_DATA_TEST_TEST, 'test')
    # print(type(text_valid)) -> <class 'pandas.core.frame.DataFrame'>

    mid_text = frame2text(data_train, data_valid)
    tokens_jieba(mid_text)
