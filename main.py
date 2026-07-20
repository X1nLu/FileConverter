import os
import sys
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(__file__))

from ui.main_window import MainWindow


def main():
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("应用错误", f"程序发生未捕获异常：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()