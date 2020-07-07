from pytube import YouTube
from pytube import YouTube
from pprint import pprint


def functionA(url, filename):
    yt = YouTube(url)
    streams = yt.streams.filter(subtype='mp4').all()
    mp4 = yt.streams.first()
    mp4.download('./', filename)
    # YouTube(url).streams.first().download()


def functionB(url, filename, index):
    try:
        yt = YouTube(url)
        print(yt.streams.get_by_itag(index).download('./', filename))
    except:
        functionB(url, filename, 22)


if __name__ == '__main__':
    url = 'https://www.youtube.com/watch?v=bfTA7GRXgEA'
    file = 'dusheng'
    functionB(url, file, 37)

