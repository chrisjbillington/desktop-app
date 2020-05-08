import sys
import tkinter
import desktop_app

desktop_app.set_process_appid('oink')

def main():
    root = tkinter.Tk(className=sys.argv[0])
    root.geometry("300x300")
    w = tkinter.Label(root, text="oink")
    w.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
    root.mainloop()

if __name__ == '__main__':
    main()