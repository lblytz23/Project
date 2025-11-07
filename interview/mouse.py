import pyautogui
import tkinter as tk
from tkinter import messagebox
import random
import time
from datetime import datetime, timedelta

def main(start_time, end_time):
    start_time = datetime.strptime(start_time, "%H:%M")
    end_time = datetime.strptime(end_time, "%H:%M")

    prev_pos = pyautogui.position()
    last_click_time = datetime.now()

    now = datetime.now().replace(year=start_time.year, month=start_time.month, day=start_time.day)

    while now.time() < end_time.time():
        now = datetime.now().replace(year=start_time.year, month=start_time.month, day=start_time.day)
        
        # 检测鼠标是否被人为移动
        current_pos = pyautogui.position()
        if prev_pos != current_pos:
            print(f"鼠标位置于 {datetime.now()} 被移动到 {current_pos}")
            response = messagebox.askyesno("检测到移动", "是否继续运行脚本?")
            if not response:
                print("脚本已终止。")
                break
            prev_pos = current_pos

        if now.time() >= start_time.time():
            # 每10秒移动鼠标至(0,0)并点击
            if (datetime.now() - last_click_time).total_seconds() >= 80:
                pyautogui.moveTo(1, 1, duration=1)
                pyautogui.click()
                last_click_time = datetime.now()
                print(f"鼠标在 {last_click_time} 移动并点击于 (0, 0)")
                time.sleep(0.5)  # 等待半秒以确保点击执行

            screen_width, screen_height = pyautogui.size()
            
            new_x = random.randint(0, screen_width)
            new_y = random.randint(0, screen_height)

            pyautogui.moveTo(new_x, new_y, duration=1)
            prev_pos = (new_x, new_y)

            time.sleep(10)

        else:
            time.sleep(30)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    start_time = "08:45"
    end_time = "16:30"

    main(start_time, end_time)