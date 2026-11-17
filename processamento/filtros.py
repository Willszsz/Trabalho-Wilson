import cv2
import numpy as np


def suavizar(cinza, config):
    tamanho = config["gaussiano"]
    return cv2.GaussianBlur(cinza, (tamanho, tamanho), 0)


def realcar(cinza, config):
    ajuste = cv2.createCLAHE(clipLimit=config["contraste_local"], tileGridSize=(8, 8))
    try:
        return ajuste.apply(cinza)
    finally:
        ajuste.collectGarbage()


def morfologia(bordas, config):
    altura, largura = bordas.shape
    x = max(3, round(largura * config["fechamento_x"]) | 1)
    y = max(3, round(altura * config["fechamento_y"]) | 1)
    return cv2.morphologyEx(bordas, cv2.MORPH_CLOSE, np.ones((y, x), np.uint8))


def textura_escura(cinza):
    largura = max(13, round(cinza.shape[1] * 0.025) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (largura, 7))
    detalhes = cv2.morphologyEx(cinza, cv2.MORPH_BLACKHAT, kernel)
    gradiente = cv2.Sobel(detalhes, cv2.CV_32F, 1, 0, ksize=3)
    gradiente = cv2.normalize(np.abs(gradiente), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    gradiente = cv2.GaussianBlur(gradiente, (3, 3), 0)
    _, binaria = cv2.threshold(gradiente, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, np.ones((3, max(7, largura // 2)), np.uint8))
