import math

import cv2
import numpy as np

from processamento.filtros import textura_escura
from processamento.imagem import escala_cinza, ordenar_pontos, retificar


def medidas_geometricas(pontos):
    pontos = ordenar_pontos(pontos)
    lados = np.linalg.norm(pontos - np.roll(pontos, -1, axis=0), axis=1)
    largura = float((lados[0] + lados[2]) / 2)
    altura = float((lados[1] + lados[3]) / 2)
    vetor = pontos[1] - pontos[0]
    angulo = math.degrees(math.atan2(float(vetor[1]), float(vetor[0])))
    return largura, altura, angulo


def retangulo_orientado(contorno):
    centro, tamanho, angulo = cv2.minAreaRect(contorno)
    largura, altura = tamanho
    if largura < altura:
        largura, altura = altura, largura
        angulo += 90
    angulo = (angulo + 90) % 180 - 90
    return centro, (largura, altura), angulo


def propostas_contornos(mascara, origem, config):
    contornos, _ = cv2.findContours(mascara, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
    limite = len(contornos) > config["limite_contornos"]
    propostas = []
    for contorno in contornos[:config["limite_contornos"]]:
        if len(contorno) < 4:
            continue
        centro, (largura, altura), angulo = retangulo_orientado(contorno)
        if altura < config["altura_min"] or largura < config["largura_min"]:
            continue
        if cv2.contourArea(contorno) / max(1, largura * altura) < 0.3:
            continue
        pontos = ordenar_pontos(cv2.boxPoints((centro, (largura, altura), angulo)))
        perimetro = cv2.arcLength(contorno, True)
        poligono = cv2.approxPolyDP(contorno, 0.025 * perimetro, True)
        if len(poligono) == 4 and cv2.isContourConvex(poligono):
            pontos = ordenar_pontos(poligono.reshape(4, 2))
        propostas.append((pontos, origem))
        if 2.6 < largura / altura < 5.2:
            ampliada = pontos.copy()
            ampliada[0] -= (pontos[3] - pontos[0]) * 0.45
            ampliada[1] -= (pontos[2] - pontos[1]) * 0.45
            propostas.append((ampliada, origem + "_ampliada"))
    return propostas, limite


def propostas_faixas(imagem, config):
    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)
    propostas = []
    mascara_total = np.zeros(imagem.shape[:2], np.uint8)
    limite = False
    for inicio, fim in [(85, 134), (35, 84), (0, 34), (135, 179)]:
        mascara = cv2.inRange(hsv, (inicio, config["saturacao_min"], config["brilho_cor_min"]), (fim, 255, 255))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((3, 5), np.uint8))
        mascara_total = cv2.bitwise_or(mascara_total, mascara)
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
        limite |= len(contornos) > config["limite_contornos"]
        for contorno in contornos[:config["limite_contornos"]]:
            if len(contorno) < 4:
                continue
            (cx, cy), (largura, faixa), angulo = retangulo_orientado(contorno)
            if largura < config["largura_min"] or faixa < 3 or not 2.6 < largura / faixa < 16:
                continue
            if abs(angulo) > config["inclinacao_max"]:
                continue
            for razao in [1.8, 2.2, 2.7, 3.3]:
                altura = largura / razao
                if not 1.5 * faixa < altura < 5.5 * faixa:
                    continue
                deslocamento = (altura - faixa) / 2
                radianos = math.radians(angulo)
                centro = (cx - math.sin(radianos) * deslocamento, cy + math.cos(radianos) * deslocamento)
                pontos = cv2.boxPoints((centro, (largura, altura), angulo))
                propostas.append((ordenar_pontos(pontos), "faixa"))
    return propostas, mascara_total, limite


def analisar_textura(recorte, config):
    altura = max(36, round(240 * recorte.shape[0] / recorte.shape[1]))
    amostra = cv2.resize(recorte, (240, altura), interpolation=cv2.INTER_AREA)
    cinza = escala_cinza(amostra)
    miolo = cinza[3:-3, 6:-6]
    p10, p90 = np.percentile(miolo, [10, 90])
    contraste = float(p90 - p10)
    if contraste < config["contraste_min"]:
        return None
    normalizada = np.clip((cinza.astype(np.float32) - p10) * 255 / max(1, contraste), 0, 255).astype(np.uint8)
    bordas = cv2.Canny(normalizada[3:-3, 6:-6], 60, 160)
    densidade = float(np.count_nonzero(bordas) / bordas.size)
    if not config["bordas_min"] <= densidade <= config["bordas_max"]:
        return None
    _, escura = cv2.threshold(normalizada, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    quantidade, _, estatisticas, centros = cv2.connectedComponentsWithStats(escura)
    marcas = []
    for indice in range(1, quantidade):
        x, y, largura, h, area = estatisticas[indice]
        if x < 3 or x + largura > 237 or y < altura * 0.1 or y + h > altura - 1:
            continue
        if not altura * 0.17 < h < altura * 0.78 or not 2 <= largura <= 48:
            continue
        if not 0.65 < h / largura < 12 or not 0.10 < area / (largura * h) < 0.95:
            continue
        marcas.append(centros[indice])
    if len(marcas) < config["marcas_min"]:
        return None
    marcas = np.asarray(marcas)
    ocupacao = float((marcas[:, 0].max() - marcas[:, 0].min()) / 240)
    if ocupacao < config["ocupacao_min"]:
        return None
    colunas = np.abs(np.diff(normalizada[int(altura * 0.32):-3, 6:-6].astype(np.float32), axis=1)).mean(axis=0)
    ativos = colunas > max(8, float(np.percentile(colunas, 60)))
    distribuicao = sum(np.any(parte) for parte in np.array_split(ativos, 6)) / 6
    hsv = cv2.cvtColor(amostra, cv2.COLOR_BGR2HSV)
    colorida = (hsv[:, :, 1] > config["saturacao_min"]) & (hsv[:, :, 2] > config["brilho_cor_min"])
    corte = max(1, round(altura * 0.35))
    faixa = float(np.clip(colorida[:corte].mean() - colorida[corte:].mean(), 0, 1))
    fundo = float((normalizada[corte:, 6:-6] > 155).mean())
    return {"contraste": contraste, "densidade": densidade, "marcas": len(marcas),
            "ocupacao": ocupacao, "distribuicao": float(distribuicao), "faixa": faixa, "fundo": fundo}


def pontuar(medidas, razao, preferida):
    formato = max(0, 1 - abs(math.log(razao / preferida)) / 1.3)
    marcas = min(medidas["marcas"] / 7, 1)
    if medidas["marcas"] > 20:
        marcas *= 0.65
    ocupacao = min(medidas["ocupacao"] / 0.72, 1)
    contraste = min(medidas["contraste"] / 120, 1)
    densidade = max(0, 1 - abs(medidas["densidade"] - 0.18) / 0.26)
    return float(0.15 * formato + 0.23 * marcas + 0.18 * ocupacao + 0.10 * contraste
                 + 0.10 * densidade + 0.09 * medidas["distribuicao"]
                 + 0.10 * medidas["faixa"] + 0.05 * min(medidas["fundo"] / 0.55, 1))


def caixa(pontos, forma):
    altura, largura = forma[:2]
    minimo = np.floor(np.min(pontos, axis=0)).astype(int)
    maximo = np.ceil(np.max(pontos, axis=0)).astype(int) + 1
    x, y = np.maximum(minimo, [0, 0])
    direita, base = np.minimum(maximo, [largura, altura])
    return [int(x), int(y), int(direita - x), int(base - y)]


def sobreposicao(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    intersecao = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    uniao = aw * ah + bw * bh - intersecao
    return intersecao / uniao if uniao else 0.0


def detectar(imagem, cinza, bordas, morfologia, config):
    faixas, mascara, limitado = propostas_faixas(imagem, config)
    _, claras = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    fechamento = cv2.morphologyEx(bordas, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    textura = textura_escura(cinza)
    propostas = faixas
    for origem, mapa in [("bordas", fechamento), ("morfologia", morfologia), ("clara", claras), ("textura", textura)]:
        novas, atingido = propostas_contornos(mapa, origem, config)
        propostas.extend(novas)
        limitado |= atingido
    candidatas = []
    altura, largura = imagem.shape[:2]
    vistas = set()
    for pontos, origem in propostas:
        w, h, angulo = medidas_geometricas(pontos)
        if h < config["altura_min"] or w < config["largura_min"]:
            continue
        razao, area = w / h, w * h / (altura * largura)
        if not config["razao_min"] <= razao <= config["razao_max"] or not config["area_min"] <= area <= config["area_max"]:
            continue
        if abs(angulo) > config["inclinacao_max"] or np.any(pontos < 0) or np.any(pontos >= [largura, altura]):
            continue
        chave = tuple((pontos / 3).round().astype(int).ravel())
        if chave in vistas:
            continue
        vistas.add(chave)
        recorte = retificar(imagem, pontos)
        medidas = analisar_textura(recorte, config)
        if medidas is None:
            continue
        candidatas.append({"pontos": pontos.tolist(), "caixa": caixa(pontos, imagem.shape),
                           "nota": pontuar(medidas, razao, config["razao_preferida"]), "origem": origem,
                           "angulo": angulo, "medidas": medidas})
    candidatas.sort(key=lambda item: item["nota"], reverse=True)
    unicas = []
    for candidata in candidatas:
        if all(sobreposicao(candidata["caixa"], outra["caixa"]) < 0.7 for outra in unicas):
            unicas.append(candidata)
    escolhida = unicas[0] if unicas and unicas[0]["nota"] >= config["nota_min"] else None
    return escolhida, unicas, {"faixas": mascara, "textura": textura}, limitado
