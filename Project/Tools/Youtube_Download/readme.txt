## 这是一个小型的Youtube视频下载器以及音频+字幕提取器。
Input:
视频网址

Output:
视频.map4
字幕.txt
字幕_带TimeStamp.dat
字幕_带TimeStamp.txt

Tricks:
对于背景非黑白的视频以及分辨率在360一下的视频，识别性能较差。
对于resize和b的参数，建议每个系列视频都进行微调。

OpenCV Subtitle-picking