# interface gráfica do romanizador (tkinter)

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from romanizacao import (EXT_DOCUMENTO, EXT_MUSICA, MODELO_WHISPER, ler_documento,
                         romanizar, salvar_txt, transcrever)

# cores:
AZUL = "#1A73C7"
AZUL_ESCURO = "#0B4A7E"
VERDE = "#2E9E5B"
VERDE_ESCURO = "#237A46"
VERDE_CLARO = "#EAF6EF"
FUNDO = "#F2F7F5"
BRANCO = "#FFFFFF"
BORDA = "#CFE3D8"
TEXTO = "#1D2D27"
CINZA = "#6E8179"
FONTE = ("Helvetica", 18)


class App:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("Romanização ucraniana")
        raiz.geometry("900x580")
        raiz.minsize(620, 440)
        raiz.configure(bg=FUNDO)

        # sem o png o app continua funcionando, só fica sem ícone
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.png")
        self.icone_pequeno = None
        if os.path.exists(caminho):
            self.icone = tk.PhotoImage(file=caminho)
            raiz.iconphoto(True, self.icone)
            # subsample só aceita fator inteiro, então o cabeçalho usa uma versão menor
            self.icone_pequeno = self.icone.subsample(max(1, self.icone.width() // 44))

        # o modelo do whisper é carregado uma vez, na primeira transcrição
        self.modelo = None
        self.ocupado = False
        # a thread de trabalho não mexe na tela; ela deposita o resultado aqui
        self.fila = queue.Queue()

        self._cabecalho()
        self._barra_inferior()  # antes do corpo, senão some ao encolher a janela
        self._corpo()
        self.entrada.focus_set()

    def _cabecalho(self):
        topo = tk.Frame(self.raiz, bg=BRANCO)
        topo.pack(fill="x")
        tk.Label(topo, image=self.icone_pequeno, bg=BRANCO).pack(side="left", padx=(20, 12), pady=10)
        tk.Label(topo, text="Romanização ucraniana", font=("Helvetica", 15, "bold"),
                 fg=AZUL_ESCURO, bg=BRANCO).pack(side="left")
        tk.Frame(self.raiz, bg=VERDE, height=3).pack(fill="x")  # faixa que separa o cabeçalho

    def _barra_inferior(self):
        barra = tk.Frame(self.raiz, bg=FUNDO)
        barra.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        # o texto só aparece enquanto um arquivo está sendo processado
        self.status = tk.Label(barra, text="", font=("Helvetica", 9), fg=CINZA, bg=FUNDO)
        self.status.pack(side="left")
        # o último pack à direita fica na ponta, por isso arquivo vem antes
        self.btn_arquivo = self._botao(barra, "Adicionar arquivo", self._escolher_arquivo, VERDE_ESCURO)
        self.btn_arquivo.pack(side="right")
        self.btn_musica = self._botao(barra, "Adicionar música", self._escolher_musica, AZUL)
        self.btn_musica.pack(side="right", padx=(0, 10))

    def _corpo(self):
        corpo = tk.Frame(self.raiz, bg=FUNDO)
        corpo.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        # uniform faz os dois painéis terem a mesma largura
        corpo.columnconfigure(0, weight=1, uniform="painel")
        corpo.columnconfigure(1, weight=1, uniform="painel")
        corpo.rowconfigure(0, weight=1)

        # entrada: texto em ucraniano, continua editável mesmo com arquivos carregados
        esquerda = self._painel(corpo, 0, "UCRANIANO", BRANCO)
        rodape = self._rodape(esquerda)
        self._botao(rodape, "Limpar", self._limpar, AZUL).pack(side="right")
        self.entrada = tk.Text(esquerda, wrap="word", font=FONTE, bg=BRANCO, fg=TEXTO,
                               bd=0, highlightthickness=0, padx=16, pady=8,
                               insertbackground=AZUL)
        self.entrada.pack(fill="both", expand=True)
        # o tk só dispara <<Modified>> quando a flag muda, então a flag é zerada a cada evento
        self.entrada.bind("<<Modified>>", self._ao_editar)

        # saída: romanização, só leitura
        direita = self._painel(corpo, 1, "ROMANIZADO", VERDE_CLARO)
        rodape = self._rodape(direita, VERDE_CLARO)
        self.btn_copiar = self._botao(rodape, "Copiar", self._copiar, VERDE)
        self.btn_copiar.pack(side="right")
        self._botao(rodape, "Baixar TXT", self._baixar, AZUL).pack(side="right", padx=(0, 10))
        # disabled impede edição, mas o texto continua selecionável
        self.saida = tk.Text(direita, wrap="word", font=FONTE, bg=VERDE_CLARO, fg=AZUL_ESCURO,
                             bd=0, highlightthickness=0, padx=16, pady=8, state="disabled")
        self.saida.pack(fill="both", expand=True)

    def _painel(self, pai, coluna, rotulo, fundo):
        quadro = tk.Frame(pai, bg=fundo, highlightthickness=1, highlightbackground=BORDA)
        quadro.grid(row=0, column=coluna, sticky="nsew",
                    padx=(0, 10) if coluna == 0 else (10, 0))
        tk.Label(quadro, text=rotulo, font=("Helvetica", 9, "bold"), fg=VERDE,
                 bg=fundo).pack(anchor="w", padx=16, pady=(12, 0))
        return quadro

    def _rodape(self, quadro, fundo=BRANCO):
        rodape = tk.Frame(quadro, bg=fundo)
        rodape.pack(side="bottom", fill="x", padx=12, pady=10)  # precisa vir antes do texto
        return rodape

    def _botao(self, pai, texto, comando, cor):
        return tk.Button(pai, text=texto, command=comando, bg=cor, fg=BRANCO,
                         activebackground=cor, activeforeground=BRANCO, relief="flat",
                         bd=0, padx=14, pady=5, font=("Helvetica", 10, "bold"), cursor="hand2")

    def _ao_editar(self, _=None):
        if self.entrada.edit_modified():
            self.entrada.edit_modified(False)
            self._atualizar()

    def _atualizar(self):
        convertido = romanizar(self.entrada.get("1.0", "end-1c"))
        self.saida.config(state="normal")
        self.saida.delete("1.0", "end")
        self.saida.insert("1.0", convertido)
        self.saida.config(state="disabled")

    def _limpar(self):
        self.entrada.delete("1.0", "end")

    def _copiar(self):
        # clipboard_* usa a área de transferência do sistema, funciona em windows, mac e linux
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(self.saida.get("1.0", "end-1c"))
        self.btn_copiar.config(text="Copiado!")
        self.raiz.after(1200, lambda: self.btn_copiar.config(text="Copiar"))

    def _baixar(self):
        texto = self.saida.get("1.0", "end-1c")
        if not texto:
            messagebox.showinfo("Nada para salvar", "escreva ou adicione um texto primeiro.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar romanização", initialfile="romanizado.txt", defaultextension=".txt",
            filetypes=[("Texto", "*.txt")])
        if caminho:
            salvar_txt(caminho, texto)

    def _escolher_musica(self):
        caminho = filedialog.askopenfilename(
            title="Escolha um áudio ou vídeo",
            filetypes=[("Áudio e vídeo", " ".join("*" + e for e in EXT_MUSICA))])
        if caminho:
            self._processar(caminho, musica=True)

    def _escolher_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Escolha um documento",
            filetypes=[("Documentos", " ".join("*" + e for e in EXT_DOCUMENTO))])
        if caminho:
            self._processar(caminho, musica=False)

    def _processar(self, caminho, musica):
        if self.ocupado:
            return
        self._ocupar(True, f"processando {os.path.basename(caminho)}…")
        # transcrever pode levar minutos; a thread evita a janela travar
        threading.Thread(target=self._trabalhar, args=(caminho, musica), daemon=True).start()
        self.raiz.after(100, self._verificar_fila)

    def _trabalhar(self, caminho, musica):
        try:
            if musica:
                if self.modelo is None:
                    from faster_whisper import WhisperModel
                    self.modelo = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
                texto = transcrever(self.modelo, caminho)
            else:
                texto = ler_documento(caminho)
            self.fila.put(("ok", texto))
        except ImportError as e:
            self.fila.put(("erro", f"{e}\n\ninstale o que falta com pip install faster-whisper pypdf python-docx"))
        except Exception as e:
            self.fila.put(("erro", str(e)))

    def _verificar_fila(self):
        try:
            estado, valor = self.fila.get_nowait()
        except queue.Empty:
            self.raiz.after(100, self._verificar_fila)
            return
        self._ocupar(False, "")
        if estado == "ok":
            self._adicionar_texto(valor)
        else:
            messagebox.showerror("Erro", valor)

    def _adicionar_texto(self, texto):
        texto = texto.strip()
        if not texto:
            messagebox.showinfo("Sem texto", "não achei texto nesse arquivo.")
            return
        atual = self.entrada.get("1.0", "end-1c")
        # se já tem texto escrito, o novo entra em outro parágrafo
        separador = "\n\n" if atual.strip() else ""
        self.entrada.insert("end", separador + texto)  # o insert dispara a romanização

    def _ocupar(self, ocupado, mensagem):
        self.ocupado = ocupado
        estado = "disabled" if ocupado else "normal"
        self.btn_musica.config(state=estado)
        self.btn_arquivo.config(state=estado)
        self.status.config(text=mensagem)
