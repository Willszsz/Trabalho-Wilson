import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

FORMATOS = {".jpg", ".jpeg", ".png"}


def carregar(caminho, config):
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ValueError(f"Arquivo inexistente ou não regular: {caminho}")
    if caminho.suffix.lower() not in FORMATOS:
        raise ValueError("Formato não suportado. Utilize JPG, JPEG ou PNG.")
    if caminho.stat().st_size > config["max_arquivo_mb"] * 1024 ** 2:
        raise ValueError("Arquivo excede o limite de tamanho configurado.")
    dados = caminho.read_bytes()
    try:
        with Image.open(io.BytesIO(dados)) as cabecalho:
            largura, altura = cabecalho.size
            if cabecalho.format not in {"JPEG", "PNG"}:
                raise ValueError("O conteúdo do arquivo não é JPEG nem PNG.")
            if largura * altura > config["max_megapixels"] * 1_000_000:
                raise ValueError("Imagem excede o limite de pixels configurado.")
            cabecalho.verify()
        with Image.open(io.BytesIO(dados)) as verificacao:
            verificacao.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as erro:
        raise ValueError(f"Imagem corrompida ou incompleta: {caminho.name}") from erro
    matriz = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if matriz is None or matriz.size == 0:
        raise ValueError(f"OpenCV não conseguiu decodificar {caminho.name}.")
    return matriz


def escala_cinza(imagem):
    if imagem.dtype != np.uint8 or imagem.ndim != 3 or imagem.shape[2] != 3:
        raise ValueError("Esperada uma matriz BGR uint8 com três canais.")
    pesos = np.array([0.114, 0.587, 0.299], dtype=np.float32)
    return np.floor(imagem.astype(np.float32) @ pesos + 0.5).clip(0, 255).astype(np.uint8)


def reduzir(imagem, lado_maximo):
    altura, largura = imagem.shape[:2]
    escala = min(1.0, lado_maximo / max(altura, largura))
    tamanho = (max(1, round(largura * escala)), max(1, round(altura * escala)))
    return cv2.resize(imagem, tamanho, interpolation=cv2.INTER_AREA)


def ordenar_pontos(pontos):
    pontos = np.asarray(pontos, dtype=np.float32).reshape(4, 2)
    centro = pontos.mean(axis=0)
    angulos = np.arctan2(pontos[:, 1] - centro[1], pontos[:, 0] - centro[0])
    pontos = pontos[np.argsort(angulos)]
    inicio = np.argmin(pontos.sum(axis=1))
    pontos = np.roll(pontos, -inicio, axis=0)
    if pontos[1, 0] < pontos[-1, 0]:
        pontos = pontos[[0, 3, 2, 1]]
    return pontos


def retificar(imagem, pontos):
    pontos = ordenar_pontos(pontos)
    largura = max(np.linalg.norm(pontos[1] - pontos[0]), np.linalg.norm(pontos[2] - pontos[3]))
    altura = max(np.linalg.norm(pontos[3] - pontos[0]), np.linalg.norm(pontos[2] - pontos[1]))
    largura, altura = max(2, round(float(largura))), max(2, round(float(altura)))
    destino = np.float32([[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]])
    transformacao = cv2.getPerspectiveTransform(pontos, destino)
    return cv2.warpPerspective(imagem, transformacao, (largura, altura), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)
