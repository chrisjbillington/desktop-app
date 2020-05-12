import sys
import tkinter
import desktop_app
from desktop_app.shell import _ModuleConfig
from win32com.shell import shell

desktop_app.set_process_appid("oink")
appid = shell.GetCurrentProcessExplicitAppUserModelID()

def main():
    root = tkinter.Tk(className=sys.argv[0])
    root.geometry("500x300")
    w = tkinter.Label(root, text="Oink!")
    w.place(relx=0.5, rely=0.3, anchor=tkinter.CENTER)
    sys_info = (
        f"sys.prefix: {sys.prefix}\n"
        f"sys.exec_prefix: {sys.exec_prefix}\n"
        f"sys.executable: {sys.executable}\n"
        f"AppUserModelID (shortcut): {_ModuleConfig.instance('oink').appid}\n"
        f"AppUserModelID (process) : {appid}"
    )
    s = tkinter.Label(root, text=sys_info, justify=tkinter.LEFT)
    s.place(relx=0.05, rely=0.5, anchor=tkinter.W)
    print(sys_info)
    root.mainloop()


if __name__ == "__main__":
    main()
