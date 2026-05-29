import sys; sys.path.insert(0, 'D:/WWW/Python/FileConverter')
from ui.main_window import MainWindow
import threading, time

def shot():
    time.sleep(1)
    import pyautogui
    pyautogui.screenshot('D:/WWW/Python/FileConverter/screenshot.png', region=(100, 100, 700, 550))
    print('OK')

app = MainWindow()
app.geometry('700x550+100+100')
app.update()
time.sleep(0.3)
app.lift()
app.update()
threading.Thread(target=shot, daemon=True).start()
time.sleep(3)
app.destroy()