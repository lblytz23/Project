from pytube import YouTube


class Youtube_Downloader():
    def __init__(self):
        self.output_path = ''

    def functionA(self, url, filename):
        yt = YouTube(url)
        streams = yt.streams.filter(subtype='mp4').all()
        mp4 = yt.streams.first()
        mp4.download(self.output_path, filename)
        # YouTube(url).streams.first().download()

    def functionB(self, url, filename, index):
        try:
            yt = YouTube(url)
            print(yt.streams.get_by_itag(index).download(self.output_path, filename))
        except:
            self.functionB(url, filename, 22)


if __name__ == '__main__':
    yd = Youtube_Downloader()
    url = 'https://www.youtube.com/watch?v=Yd7R3JIFvnY&list=PLOAQYZPRn2V4iTh0XRB_-EHNktK_ai7kl&index=1'
    file = '视频1'
    yd.functionB(url, file, 37)
