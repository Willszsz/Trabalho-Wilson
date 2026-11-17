import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import cv2

from processamento.imagem import FORMATOS


def criar_destino(pasta, entrada):
    nome = re.sub(r"[^\w.-]", "_", Path(entrada).stem)[:60] or "imagem"
    identificador = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:8]
    destino = Path(pasta).resolve() / f"{nome}_{identificador}"
    destino.mkdir(parents=True, exist_ok=False)
    return destino


def salvar_imagem(caminho, imagem):
    caminho = Path(caminho)
    if imagem is None or imagem.size == 0:
        raise ValueError("Não é possível salvar uma imagem vazia.")
    sucesso, dados = cv2.imencode(".png", imagem)
    if not sucesso:
        raise OSError("OpenCV não conseguiu codificar a imagem.")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("xb") as arquivo:
        arquivo.write(dados.tobytes())
    if caminho.stat().st_size == 0:
        raise OSError(f"Arquivo gerado está vazio: {caminho}")
    return str(caminho)


def salvar_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False)
    with caminho.open("x", encoding="utf-8") as arquivo:
        arquivo.write(texto + "\n")


def listar_imagens(pasta, saida, recursivo=False):
    pasta, saida = Path(pasta).resolve(), Path(saida).resolve()
    if not pasta.is_dir():
        raise ValueError(f"Pasta inexistente: {pasta}")
    if pasta == saida or saida in pasta.parents:
        raise ValueError("A entrada não pode ser a pasta de resultados nem estar dentro dela.")
    arquivos = pasta.rglob("*") if recursivo else pasta.iterdir()
    return sorted(p for p in arquivos if p.is_file() and p.suffix.lower() in FORMATOS
                  and saida not in p.resolve().parents)


def historico(pasta):
    registros = []
    for arquivo in sorted(Path(pasta).glob("*/resultado.json"), reverse=True):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            if isinstance(dados, dict) and {"arquivo", "estado"} <= dados.keys():
                dados["relatorio"] = str(arquivo.resolve())
                registros.append(dados)
        except (OSError, ValueError):
            continue
    return registros
