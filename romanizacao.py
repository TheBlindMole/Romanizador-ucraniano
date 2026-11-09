# lógica do romanizador: sem nada de interface

import os
import re

# letras com som fixo
TABELA = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d",
    "е": "e", "ж": "zh", "з": "z", "и": "y", "і": "i", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "'": "", "’": "", "ʼ": "",
}

# є, ї, ю, я mudam conforme a letra anterior:
# no começo da palavra (ou depois de ь e apóstrofo) viram ye, yi, yu, ya;
# no meio, depois de qualquer outra letra, viram ie, i, iu, ia (марія -> mariia)
CONTEXTUAIS = {
    "є": ("ye", "ie"),
    "ї": ("yi", "i"),
    "ю": ("yu", "iu"),
    "я": ("ya", "ia"),
}
INICIO = ("", "ь", "'", "’", "ʼ")

# й depois de vogal vira "i" (гайдай -> haidai), nos outros casos "y"
VOGAIS = frozenset("аеєиіїоуюя")

# palavra = letras, com apóstrofo só entre letras (assim as aspas ao redor não somem)
PALAVRA = re.compile(r"[а-яіїєґ]+(?:['’ʼ][а-яіїєґ]+)*", re.IGNORECASE)

# formatos aceitos pela interface
EXT_MUSICA = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".mp4", ".mkv", ".webm")
EXT_DOCUMENTO = (".txt", ".md", ".csv", ".pdf", ".docx")

# "small" tem boa qualidade em ucraniano e roda no cpu sem travar muito
MODELO_WHISPER = "small"


def _palavra(p):
    t = p.lower()  # a tabela é toda em minúsculas
    saida = []
    for i, c in enumerate(t):
        ant = t[i - 1] if i else ""  # a letra anterior decide o som
        if c == "й":
            saida.append("i" if ant in VOGAIS else "y")
        elif c in CONTEXTUAIS:
            inicio, meio = CONTEXTUAIS[c]
            saida.append(inicio if ant in INICIO else meio)
        else:
            saida.append(TABELA.get(c, c))  # letra que não é ucraniana passa igual
    r = "".join(saida)

    # caixa: palavra toda maiúscula continua maiúscula, senão só a primeira letra
    if p.isupper():
        return r.upper()
    if p[0].isupper():
        return r[:1].upper() + r[1:]
    return r


def romanizar(texto):
    # troca só as palavras; espaços, números e pontuação ficam como estão
    return PALAVRA.sub(lambda m: _palavra(m.group()), texto)


def ler_documento(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    # pdf e docx têm bibliotecas próprias, importadas só quando usadas
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(caminho).pages)
    if ext == ".docx":
        from docx import Document
        return "\n".join(p.text for p in Document(caminho).paragraphs)
    # utf-8-sig tira o BOM que alguns editores põem no começo do arquivo
    with open(caminho, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def transcrever(modelo, caminho):
    # language="uk" pula a detecção automática; vad_filter corta os trechos sem fala
    segmentos, _ = modelo.transcribe(caminho, language="uk", vad_filter=True)
    return " ".join(s.text.strip() for s in segmentos)


def salvar_txt(caminho, texto):
    # newline="" deixa o arquivo com as quebras de linha que foram escritas, sem trocar
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto)
