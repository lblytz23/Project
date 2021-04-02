from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
from gensim.models.keyedvectors import KeyedVectors
from NLG_Baidu.utils.data_utils import dump_pkl
from NLG_Baidu.utils.embedding_utils import Vocab
from NLG_Baidu.utils.config import save_wv_model_path
import numpy as np


def read_lines(path, col_sep=None):
    lines = []
    with open(path, mode='r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if col_sep:
                if col_sep in line:
                    lines.append(line)
            else:
                lines.append(line)
    return lines


def extract_sentence(train_x_seg_path, train_y_seg_path, test_seg_path):
    ret = []
    lines = read_lines(train_x_seg_path)
    lines += read_lines(train_y_seg_path)
    lines += read_lines(test_seg_path)
    for line in lines:
        ret.append(line)
    return ret


def save_sentence(lines, sentence_path):
    with open(sentence_path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write('%s\n' % line.strip())
    print('save sentence:%s' % sentence_path)


# 这里我们要存储一个类似鹅厂的词向量那样的结构。'KEY':[.........]。用于Feed给神经网络，但是神经网络不知道什么是'KEY',
# 所以我们Feed给神经网络词向量的同时，还要提供一个Dict给神经网络，也就是word_dict_build中生成的产物。
# min_count：根据词频截断
def build_bk(train_x_seg_path, test_y_seg_path, test_seg_path, out_path=None, sentence_path='',
          w2v_bin_path="w2v.bin", min_count=100):
    # 取到所有的分词之后的Text数据
    sentences = extract_sentence(train_x_seg_path, test_y_seg_path, test_seg_path)
    save_sentence(sentences, sentence_path)
    print('train w2v model...')
    # train model
    # size_256是因为要迎合之后的项目要求。
    w2v = Word2Vec(sg=1, sentences=LineSentence(sentence_path),
                   size=256, window=5, min_count=min_count, iter=5)
    # 因为没有追加语料，所以保存模式使用2进制保存。
    w2v.wv.save_word2vec_format(w2v_bin_path, binary=True)
    print("save %s ok." % w2v_bin_path)
    # test
    sim = w2v.wv.similarity('技师', '车主')
    print('技师 vs 车主 similarity score:', sim)

    # build embedding_matrix
    # load model
    model = KeyedVectors.load_word2vec_format(w2v_bin_path, binary=True)
    word_dict = {}

    # model是一个词向量，model.vocab可以拿到向量空间的所有词表。
    for word in model.vocab:
        word_dict[word] = model[word]
    dump_pkl(word_dict, out_path, overwrite=True)
    print(word_dict['汽车'])


# 由于之前的build中，但当想使用外部词向量时，或者自己训练词向量时后期会出现很多UNK词的情况，如此利用不太好。
# 而且每一次从id转文字时，都需要加载一次model。因此对build函数做一次优化。
def build(train_x_seg_path, test_y_seg_path, test_seg_path, out_path=None, sentence_path='', vocab_path='',
          w2v_bin_path=save_wv_model_path, min_count=100):
    vocab = Vocab(vocab_path, 30000)  # TODO: vocab_size
    sentences = extract_sentence(train_x_seg_path, test_y_seg_path, test_seg_path)
    save_sentence(sentences, sentence_path)
    print('train w2v model...')
    # train model
    w2v = Word2Vec(sg=1, sentences=LineSentence(sentence_path),
                   size=256, window=5, min_count=min_count, iter=5)
    w2v.wv.save_word2vec_format(w2v_bin_path, binary=True)
    model = KeyedVectors.load_word2vec_format(w2v_bin_path, binary=True)
    word_dict = {}

    for word, index in vocab.word2id.items():
        if word in model.vocab:
            word_dict[index] = model[word]
        else:
            word_dict[index] = np.random.uniform(-0.025, 0.025, 256)
    dump_pkl(word_dict, out_path, overwrite=True)


if __name__ == '__main__':
    build('../data/train_set.seg_x.txt',
          '../data/train_set.seg_y.txt',
          '../data/test_set.seg_x.txt',
          out_path='../data/word2vec.txt',
          sentence_path='../data/sentences.txt', )
