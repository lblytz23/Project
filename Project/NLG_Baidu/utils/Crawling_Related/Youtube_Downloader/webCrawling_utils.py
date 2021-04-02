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
    url = 'https://www.youtube.com/watch?v=O7U2PiENOec'
    file = 'Watermelon Smash Challenge play with Gaby Alex and Mommy'
    file = file.replace(':', '_')
    file = file.replace(' ', '_')
    print(file)
    yd.functionB(url, file, 37)
