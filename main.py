#!/usr/bin/env python3
# ponto de entrada: só abre a janela, a lógica fica em romanizacao.py e a tela em interface.py

import tkinter as tk

from interface import App

if __name__ == "__main__":
    raiz = tk.Tk()
    App(raiz)
    raiz.mainloop()
