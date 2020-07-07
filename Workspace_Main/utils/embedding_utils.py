class Vocab:
    # Input: vocab.txt
    def __init__(self, vocab_file, vocab_max_size=None):
        # 假设样本输入为400个词，有些长度超过400，要截取后在最后加上'<STOP>'，而不足400的需要在'<STOP>'后面用'<PAD>'补全
        self.PAD_TOKEN = '<PAD>'
        self.UNKNOWN_TOKEN = '<UNK>'
        self.START_DECODING = '<START>'
        self.STOP_DECODING = '<STOP>'

        self.MASK = ['<PAD>', '<UNK>', '<START>', '<STOP>']
        # 真正的数据应该从index=4开始做编码
        self.MASK_LEN = len(self.MASK)
        self.pad_token_index = self.MASK.index(self.PAD_TOKEN)
        self.unk_token_index = self.MASK.index(self.UNKNOWN_TOKEN)
        self.start_token_index = self.MASK.index(self.START_DECODING)
        self.stop_token_index = self.MASK.index(self.STOP_DECODING)
        # 真正的数据应该从index=4开始做编码 (针对word2id时)
        self.word2id, self.id2word = self.load_vocab(vocab_file, vocab_max_size)
        self.count = len(self.word2id)

    def load_vocab(self, vocab_file, vocab_max_size=None):
        # 建立字典，将4个特殊字符放入初始字表中
        vocab = {mask: index for index, mask in enumerate(self.MASK)}
        reverse_vocab = {index: mask for index, mask in enumerate(self.MASK)}
        # 打开vocab.txt文件
        for line in open(vocab_file, 'r', encoding='utf-8').readlines():
            word, index = line.strip().split('\t')
            index = int(index)
            # 注意末尾一定要减一
            if vocab_max_size and index > vocab_max_size - self.MASK_LEN - 1:
                # 如果超出长度，则break
                break
            # 未超出长度，需要填词
            vocab[word] = index + self.MASK_LEN
            reverse_vocab[index + self.MASK_LEN] = word
        return vocab, reverse_vocab

    # 辅助工具函数，输入的时候要用。当有文字输入时，只要调用这个方法word_to_id,则可以得到对应的id
    def word_to_id(self, word):
        if word not in self.word2id:
            return self.word2id[self.UNKNOWN_TOKEN]
        return self.word2id[word]

    # 辅助工具函数(查询工具)，id对应的文字是什么时，
    def id_to_word(self, word_id):
        if word_id not in self.id2word:
            
            # 返回UNK,或者报错
            return self.UNKNOWN_TOKEN
        return self.id2word[word_id]

    def size(self):
        # 查看词表大小
        return self.count
