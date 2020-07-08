import cv2
from PIL import Image
import numpy as np
import os
import datetime

# Plz install ffmpeg.exe before call those functions. Just open source code
# can be found from github, but Below is the link that provide it already
# compiled and ready to go. https://ffmpeg.zeranoe.com/builds/
# Then add the bin path in the environment variables


# Slice Size Adjustment. Prepossessing
def ciao(filename, skip_f):
    videoCap = cv2.VideoCapture(filename)

    # 帧频
    fps = videoCap.get(cv2.CAP_PROP_FPS)
    # 视频总帧数
    total_frames = int(videoCap.get(cv2.CAP_PROP_FRAME_COUNT))
    # 图像尺寸
    image_size = (int(videoCap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(videoCap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    print(fps)
    print(total_frames)
    print(image_size)

    sucess, frame = videoCap.read()

    for i in range(skip_f):
        sucess, frame = videoCap.read()

    img = Image.fromarray(frame)
    img.show()
    #
    im = frame[:, :, 0]
    im = im[620:660, :]
    img = Image.fromarray(im)
    img.save('C:/Users/b-luan/PycharmProjects/ciao/units/test.png')
    input('Plz check and modify the ROI size')


# Main
class Pic_ROI():
    def __init__(self, video_filename, skip_frames):
        self.video_filename = video_filename
        self.skip_frames = skip_frames
        pass

    def format_time(self, second):
        hours = second // 3600
        minutes = (second - hours * 3600) // 60
        second = second - hours * 3600 - minutes * 60
        t = datetime.time(hour=hours, minute=minutes, second=second)
        return datetime.time.isoformat(t)

    def cal_stderr(self, img, imgo=None):
        if imgo is None:
            return (img ** 2).sum() / img.size * 100
        else:
            return ((img - imgo) ** 2).sum() / img.size * 100

    def save_image(self, ex_folder, img: Image, starts: int, ends: int):
        # 保存字幕图片到文件夹
        start_time = self.format_time(starts).replace(':', '')
        end_time = self.format_time(ends).replace(':', '')
        timeline = '-'.join([start_time, end_time]) + ".jpg"
        try:
            imgname = os.path.join(ex_folder, timeline)
            img.save(imgname)
            print('export subtitle at %s' % timeline)
        except Exception:
            print('export subtitle at %s error' % timeline)

    def export_subtitle(self):
        ex_folder = os.path.splitext(self.video_filename)[0]
        if not os.path.exists(ex_folder):
            os.mkdir(ex_folder)
        videoCap = cv2.VideoCapture(self.video_filename)
        for i in range(self.skip_frames):
            videoCap.read()
        start_frame = self.skip_frames
        curr_frame = self.skip_frames
        fps = videoCap.get(cv2.CAP_PROP_FPS)
        success = True
        subtitle_img = None
        last_img = None
        img_count = 0
        while success:
            for j in range(9):
                videoCap.read()
                curr_frame += 1
            success, frame = videoCap.read()
            curr_frame += 1
            if frame is None:
                print('video: %s finish at %d frame.' % (self.video_filename, curr_frame))
                break

            img = frame[:, :, 0]
            img = img[620:660, :]
            _, img = cv2.threshold(img, 190, 255, cv2.THRESH_BINARY_INV)
            # _, img = cv2.threshold(img, 250, 255, cv2.THRESH_TRUNC)

            if self.cal_stderr(img) < 1:
                continue

            if img_count == 0:
                subtitle_img = img
                print('video: %s add subtitle at %d frame.' % (self.video_filename, curr_frame))
                last_img = img
                img_count += 1
            elif img_count > 10:
                img_count = 0
                subtitle_img = Image.fromarray(subtitle_img)
                self.save_image(ex_folder, subtitle_img, int(start_frame / fps), int(curr_frame / fps))
                start_frame = curr_frame  # 开始时间往后移
            else:
                if self.cal_stderr(img, last_img) > 1:
                    subtitle_img = np.vstack((subtitle_img, img))
                    last_img = img
                    img_count += 1
                    print('video: %s add subtitle at %d frame.' % (self.video_filename, curr_frame))
        if img_count > 0:
            subtitle_img = Image.fromarray(subtitle_img)
            self.save_image(ex_folder, subtitle_img, int(start_frame / fps), int(curr_frame / fps))
        print('video: %s export subtitle finish!' % self.video_filename)

    def run(self):
        self.export_subtitle()


if __name__ == "__main__":
    video_filename = 'video/test.mp4'
    # ciao(video_filename, 900)
    pr = Pic_ROI(video_filename, 900)
    pr.run()
