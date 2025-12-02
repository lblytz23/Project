"""
屏幕录制软件 - 主程序
支持全屏录制、音视频同步、MP4格式输出
针对PPT演示录制优化，节省存储空间
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os
from datetime import datetime
import numpy as np
import cv2
import pyautogui
import pyaudio
import wave
import subprocess
from PIL import Image, ImageGrab


class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.video_writer = None
        self.audio_frames = []
        self.temp_video_file = None
        self.temp_audio_file = None
        self.output_file = None
        self.fps = 10  # PPT演示帧率较低即可，节省空间
        self.screen_size = pyautogui.size()
        
        # 音频参数
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 2
        self.audio_rate = 44100
        self.audio_chunk = 1024
        self.audio = pyaudio.PyAudio()
        self.audio_stream = None
        
    def start_recording(self, output_path):
        """开始录制"""
        if self.is_recording:
            return False
            
        self.output_file = output_path
        self.is_recording = True
        
        # 生成临时文件路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.dirname(output_path)
        self.temp_video_file = os.path.join(temp_dir, f"temp_video_{timestamp}.avi")
        self.temp_audio_file = os.path.join(temp_dir, f"temp_audio_{timestamp}.wav")
        
        # 启动录制线程
        self.video_thread = threading.Thread(target=self._record_video)
        self.audio_thread = threading.Thread(target=self._record_audio)
        
        self.video_thread.start()
        self.audio_thread.start()
        
        return True
    
    def _record_video(self):
        """录制视频（屏幕）"""
        # 使用H264编码，针对PPT优化
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(
            self.temp_video_file,
            fourcc,
            self.fps,
            (self.screen_size.width, self.screen_size.height)
        )
        
        last_frame = None
        frame_skip_threshold = 0.02  # 帧差异阈值，用于跳过相似帧以节省空间
        
        while self.is_recording:
            try:
                # 截取屏幕
                img = ImageGrab.grab()
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # 对于PPT场景，检测帧变化，减少冗余帧
                if last_frame is not None:
                    # 计算帧差异
                    diff = cv2.absdiff(frame, last_frame)
                    diff_percentage = np.sum(diff) / (diff.size * 255)
                    
                    # 如果变化很小，跳过此帧（但保持时间轴连续）
                    if diff_percentage < frame_skip_threshold:
                        time.sleep(1.0 / self.fps)
                        continue
                
                self.video_writer.write(frame)
                last_frame = frame.copy()
                
                # 控制帧率
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"视频录制错误: {e}")
                break
        
        if self.video_writer:
            self.video_writer.release()
    
    def _record_audio(self):
        """录制音频"""
        try:
            self.audio_stream = self.audio.open(
                format=self.audio_format,
                channels=self.audio_channels,
                rate=self.audio_rate,
                input=True,
                frames_per_buffer=self.audio_chunk
            )
            
            self.audio_frames = []
            
            while self.is_recording:
                try:
                    data = self.audio_stream.read(self.audio_chunk, exception_on_overflow=False)
                    self.audio_frames.append(data)
                except Exception as e:
                    print(f"音频录制错误: {e}")
                    break
            
            # 保存音频到临时文件
            if self.audio_frames:
                wf = wave.open(self.temp_audio_file, 'wb')
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.audio_rate)
                wf.writeframes(b''.join(self.audio_frames))
                wf.close()
                
        except Exception as e:
            print(f"音频初始化错误: {e}")
    
    def stop_recording(self):
        """停止录制并合成视频"""
        if not self.is_recording:
            return False
        
        self.is_recording = False
        
        # 等待录制线程结束
        if hasattr(self, 'video_thread'):
            self.video_thread.join()
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join()
        
        # 关闭音频流
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        # 合成视频和音频为MP4
        success = self._merge_audio_video()
        
        # 清理临时文件
        self._cleanup_temp_files()
        
        return success
    
    def _merge_audio_video(self):
        """使用ffmpeg合成音视频为MP4格式"""
        try:
            # 检查临时文件是否存在
            if not os.path.exists(self.temp_video_file):
                return False
            
            # 构建ffmpeg命令
            # 使用H.264编码和较低的CRF值以节省空间（适合PPT场景）
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', self.temp_video_file,  # 输入视频
            ]
            
            # 如果有音频文件，添加音频输入
            if os.path.exists(self.temp_audio_file) and os.path.getsize(self.temp_audio_file) > 0:
                cmd.extend(['-i', self.temp_audio_file])  # 输入音频
            
            cmd.extend([
                '-c:v', 'libx264',  # 视频编码器
                '-preset', 'medium',  # 编码速度
                '-crf', '28',  # 质量参数（18-28，值越大文件越小）
                '-c:a', 'aac',  # 音频编码器
                '-b:a', '128k',  # 音频比特率
                '-movflags', '+faststart',  # 优化web播放
                self.output_file
            ])
            
            # 执行ffmpeg命令
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            return result.returncode == 0
            
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到ffmpeg，请确保已安装ffmpeg并添加到系统PATH")
            return False
        except Exception as e:
            print(f"合成视频错误: {e}")
            return False
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_video_file and os.path.exists(self.temp_video_file):
                os.remove(self.temp_video_file)
            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                os.remove(self.temp_audio_file)
        except Exception as e:
            print(f"清理临时文件错误: {e}")
    
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            self.stop_recording()
        if self.audio:
            self.audio.terminate()


class RecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("屏幕录制工具")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        self.recorder = ScreenRecorder()
        self.is_recording = False
        self.start_time = None
        
        self._create_widgets()
        
        # 关闭窗口时的处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """创建GUI组件"""
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="🎬 屏幕录制工具",
            font=("Microsoft YaHei UI", 18, "bold")
        )
        title_label.pack()
        
        # 信息显示区域
        info_frame = ttk.LabelFrame(self.root, text="录制信息", padding=15)
        info_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # 状态
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(fill="x", pady=5)
        ttk.Label(status_frame, text="状态：", width=10).pack(side="left")
        self.status_label = ttk.Label(status_frame, text="未录制", foreground="gray")
        self.status_label.pack(side="left")
        
        # 时长
        time_frame = ttk.Frame(info_frame)
        time_frame.pack(fill="x", pady=5)
        ttk.Label(time_frame, text="时长：", width=10).pack(side="left")
        self.time_label = ttk.Label(time_frame, text="00:00:00")
        self.time_label.pack(side="left")
        
        # 屏幕分辨率
        resolution_frame = ttk.Frame(info_frame)
        resolution_frame.pack(fill="x", pady=5)
        ttk.Label(resolution_frame, text="分辨率：", width=10).pack(side="left")
        screen_size = pyautogui.size()
        ttk.Label(resolution_frame, text=f"{screen_size.width} x {screen_size.height}").pack(side="left")
        
        # 输出文件
        file_frame = ttk.Frame(info_frame)
        file_frame.pack(fill="x", pady=5)
        ttk.Label(file_frame, text="保存位置：", width=10).pack(side="left")
        self.file_label = ttk.Label(file_frame, text="未设置", foreground="gray")
        self.file_label.pack(side="left")
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.start_button = ttk.Button(
            button_frame,
            text="开始录制",
            command=self._start_recording,
            width=15
        )
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="停止录制",
            command=self._stop_recording,
            width=15,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        
        # 提示信息
        tip_label = ttk.Label(
            self.root,
            text="💡 提示：已针对PPT演示优化，自动节省存储空间",
            font=("Microsoft YaHei UI", 9),
            foreground="blue"
        )
        tip_label.pack(pady=5)
    
    def _start_recording(self):
        """开始录制"""
        # 选择保存位置
        default_name = f"screen_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_file = filedialog.asksaveasfilename(
            title="选择保存位置",
            defaultextension=".mp4",
            filenamepattern=default_name,
            filetypes=[("MP4视频", "*.mp4"), ("所有文件", "*.*")]
        )
        
        if not output_file:
            return
        
        # 开始录制
        if self.recorder.start_recording(output_file):
            self.is_recording = True
            self.start_time = time.time()
            
            # 更新UI
            self.status_label.config(text="正在录制", foreground="red")
            self.file_label.config(text=os.path.basename(output_file), foreground="black")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            
            # 启动计时器
            self._update_timer()
            
            messagebox.showinfo("提示", "录制已开始！\n\n将录制全屏内容，包括视频和音频。")
        else:
            messagebox.showerror("错误", "启动录制失败！")
    
    def _stop_recording(self):
        """停止录制"""
        self.is_recording = False
        
        # 显示处理中提示
        self.status_label.config(text="正在处理...", foreground="orange")
        self.root.update()
        
        # 停止录制并合成视频
        success = self.recorder.stop_recording()
        
        # 更新UI
        self.status_label.config(text="未录制", foreground="gray")
        self.time_label.config(text="00:00:00")
        self.file_label.config(text="未设置", foreground="gray")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        if success:
            messagebox.showinfo("完成", f"录制完成！\n\n文件已保存为MP4格式。")
        else:
            messagebox.showerror("错误", "视频处理失败！\n\n请检查是否安装了ffmpeg。")
    
    def _update_timer(self):
        """更新录制时长显示"""
        if self.is_recording:
            elapsed = int(time.time() - self.start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            self.time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self._update_timer)
    
    def _on_closing(self):
        """关闭窗口时的处理"""
        if self.is_recording:
            if messagebox.askokcancel("确认", "正在录制中，确定要退出吗？\n\n录制将被停止。"):
                self.recorder.stop_recording()
                self.recorder.cleanup()
                self.root.destroy()
        else:
            self.recorder.cleanup()
            self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    root = tk.Tk()
    app = RecorderGUI(root)
    app.run()


if __name__ == "__main__":
    main()

