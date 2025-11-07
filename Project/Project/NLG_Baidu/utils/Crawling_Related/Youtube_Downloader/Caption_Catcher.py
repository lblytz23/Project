# -*-coding:utf-8-*-

from PIL import Image, ImageEnhance
import pytesseract
import time

# Install "Tess doc" before run those functions
# Then add the bin path in the environment variables


def pic_to_word(filepath, filename, resize_num, b):
    content_a = ''
    try:
        time1 = time.time()
        im = Image.open(str(filepath) + str(filename))
        im = im.resize((im.width * int(resize_num), im.height * int(resize_num)))
        imgry = im.convert('L')
        sharpness = ImageEnhance.Contrast(imgry)
        sharp_img = sharpness.enhance(b)
        content_a = pytesseract.image_to_string(sharp_img, lang='chi_sim')
        time2 = time.time()
        print('processing time: %s s' % (time2 - time1))
    except Exception as e:
        print("{0}".format(str(e)))

    return content_a


def dict_create(file):
    fr = open(file, 'r', encoding='utf8')
    dic = {}
    keys = []
    for line in fr:
        v = line.strip().split('\t')
        dic[v[0]] = v[1]
        keys.append(v[0])
    fr.close()
    return dic


def sort_out(sentence):
    sort_source = dict_create('sort.txt')
    sentence_new = ''
    for key in sort_source:
        if key in sentence:
            sentence = sentence.replace(key, sort_source[key])
            sentence_new = sentence
        else:
            sentence_new = sentence
    return sentence_new


if __name__ == '__main__':
    filepath = "C:/Users/b-luan/PycharmProjects/ciao/units/test/"
    filename = "001421-001434.jpg"
    resize_num = 3
    b = 5.0
    content = pic_to_word(filepath, filename, resize_num, b)
    op = sort_out(content)
    print(op)
