import cv2
import numpy as np

from processamento.imagem import escala_cinza, ordenar_pontos

LARGURA_JANELA = 320
CROMA_COR = 0.35
CROMA_NEUTRO = 0.30
TOLERANCIA_MATIZ = 22
LIMIAR_COLUNA = 0.20
LIMIAR_LINHA = 0.25


def mapa_bilinear(pontos, s, t):
    p0, p1, p2, p3 = pontos
    return (1 - s) * (1 - t) * p0 + s * (1 - t) * p1 + s * t * p2 + (1 - s) * t * p3


def quadrilatero(pontos, esquerda, direita, topo, base):
    return np.float32([mapa_bilinear(pontos, esquerda, topo), mapa_bilinear(pontos, direita, topo),
                       mapa_bilinear(pontos, direita, base), mapa_bilinear(pontos, esquerda, base)])


def janela_retificada(imagem, pontos, expansao_x, expansao_y):
    largura = (np.linalg.norm(pontos[1] - pontos[0]) + np.linalg.norm(pontos[2] - pontos[3])) / 2
    altura = (np.linalg.norm(pontos[3] - pontos[0]) + np.linalg.norm(pontos[2] - pontos[1])) / 2
    total_x, total_y = 1 + 2 * expansao_x, 1 + 2 * expansao_y
    largura_janela = LARGURA_JANELA
    altura_janela = max(40, round(largura_janela * altura * total_y / (largura * total_x)))
    origem = quadrilatero(pontos, -expansao_x, 1 + expansao_x, -expansao_y, 1 + expansao_y)
    destino = np.float32([[0, 0], [largura_janela, 0], [largura_janela, altura_janela], [0, altura_janela]])
    transformacao = cv2.getPerspectiveTransform(origem, destino)
    janela = cv2.warpPerspective(imagem, transformacao, (largura_janela, altura_janela),
                                 flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    return janela, largura, altura


def classificar(janela, esquerda, direita, topo, base):
    cinza = escala_cinza(janela).astype(np.int32)
    canais = janela.astype(np.int32)
    maximo, minimo = canais.max(axis=2), canais.min(axis=2)
    croma = np.where(maximo > 0, (maximo - minimo) / np.maximum(maximo, 1), 0.0)
    matiz = cv2.cvtColor(janela, cv2.COLOR_BGR2HSV)[:, :, 0].astype(np.float32) * 2
    regiao = cinza[topo:base + 1, esquerda:direita + 1].astype(np.uint8)
    limiar, _ = cv2.threshold(regiao, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    corte = topo + round((base - topo) * 0.4)
    superior = (slice(topo, corte + 1), slice(esquerda, direita + 1))
    coloridos = (croma[superior] >= CROMA_COR) & (cinza[superior] > 35)
    histograma = np.bincount((matiz[superior][coloridos] // 10).astype(int) % 36, minlength=36)
    vizinhanca = histograma + np.roll(histograma, 1) + np.roll(histograma, -1)
    moda = int(np.argmax(vizinhanca))
    tem_faixa = bool(vizinhanca[moda] >= coloridos.size * 0.12)
    distancia = np.abs(matiz - (moda * 10 + 5)) % 360
    distancia = np.minimum(distancia, 360 - distancia)
    neutro = (cinza >= limiar) & (croma < CROMA_NEUTRO)
    faixa = tem_faixa & (croma >= CROMA_NEUTRO) & (distancia <= TOLERANCIA_MATIZ)
    return neutro, faixa, tem_faixa, cinza


def suavizar(valores):
    return np.convolve(np.pad(valores, 1, mode="edge"), np.ones(3) / 3, mode="valid")


def fronteira(valores, centro, sentido, lacuna, limiar, padrao):
    consecutivas = 0
    indice = centro
    while 0 <= indice < len(valores):
        if valores[indice] < limiar:
            consecutivas += 1
            if consecutivas >= lacuna:
                return indice - sentido * lacuna
        else:
            consecutivas = 0
        indice += sentido
    return padrao


def limites(neutro, faixa, tem_faixa, esquerda0, direita0, topo0, base0):
    divisao = topo0 + round((base0 - topo0) * 0.42)
    corpo_colunas = neutro[divisao:base0 + 1].mean(axis=0)
    if tem_faixa:
        colunas = np.minimum(faixa[topo0:divisao].mean(axis=0), corpo_colunas)
    else:
        colunas = neutro[topo0:base0 + 1].mean(axis=0)
    colunas = suavizar(colunas)
    centro_x = neutro.shape[1] // 2
    lacuna_x = max(3, round(0.04 * (direita0 - esquerda0)))
    esquerda = fronteira(colunas, centro_x, -1, lacuna_x, LIMIAR_COLUNA, esquerda0)
    direita = fronteira(colunas, centro_x, 1, lacuna_x, LIMIAR_COLUNA, direita0)
    if direita - esquerda < (direita0 - esquerda0) / 2:
        return None
    linhas_faixa = faixa[:, esquerda:direita + 1].mean(axis=1)
    linhas_corpo = neutro[:, esquerda:direita + 1].mean(axis=1)
    lacuna_y = max(2, round(0.02 * (base0 - topo0)))
    if tem_faixa:
        inicio_topo = topo0 + int(np.argmax(linhas_faixa[topo0:divisao + 1]))
        inicio_base = divisao + int(np.argmax(linhas_corpo[divisao:base0 + 1]))
    else:
        inicio_topo = inicio_base = neutro.shape[0] // 2
    topo = fronteira(linhas_faixa if tem_faixa else linhas_corpo, inicio_topo, -1, lacuna_y, LIMIAR_LINHA, topo0)
    base = fronteira(linhas_corpo, inicio_base, 1, lacuna_y, LIMIAR_LINHA, base0)
    return esquerda, direita, topo, base


def faixa_acima(janela, neutro, esquerda0, direita0, topo0, base0, config):
    hsv = cv2.cvtColor(janela, cv2.COLOR_BGR2HSV)
    saturada = (hsv[:, :, 1] >= config["saturacao_min"]) & (hsv[:, :, 2] >= config["brilho_cor_min"])
    matiz = hsv[:, :, 0].astype(np.int32) * 2
    altura_regiao = base0 - topo0
    faixa_busca = slice(max(0, topo0 - round(altura_regiao * 0.5)), topo0 + round(altura_regiao * 0.15))
    regiao = (faixa_busca, slice(esquerda0, direita0 + 1))
    if saturada[regiao].mean() < 0.15:
        return None
    histograma = np.bincount(matiz[regiao][saturada[regiao]] // 10 % 36, minlength=36)
    moda = int(np.argmax(histograma + np.roll(histograma, 1) + np.roll(histograma, -1)))
    distancia = np.abs(matiz - (moda * 10 + 5)) % 360
    colorida = saturada & (np.minimum(distancia, 360 - distancia) <= TOLERANCIA_MATIZ)
    linhas = colorida[faixa_busca, esquerda0:direita0 + 1].mean(axis=1)
    if linhas.max() < 0.6:
        return None
    melhor = faixa_busca.start + int(np.argmax(linhas))
    colunas = suavizar(colorida[melhor].astype(np.float32))
    centro_x = (esquerda0 + direita0) // 2
    if colunas[centro_x] < 0.5:
        return None
    lacuna = max(3, round(0.04 * (direita0 - esquerda0)))
    esquerda = fronteira(colunas, centro_x, -1, lacuna, 0.5, None)
    direita = fronteira(colunas, centro_x, 1, lacuna, 0.5, None)
    if esquerda is None or direita is None:
        return None
    faixa_linhas = colorida[:, esquerda:direita + 1].mean(axis=1)
    topo = fronteira(faixa_linhas, melhor, -1, 2, 0.5, None)
    fim_faixa = fronteira(faixa_linhas, melhor, 1, 2, 0.5, None)
    if topo is None or fim_faixa is None or fim_faixa < topo0 - altura_regiao * 0.15:
        return None
    corpo = neutro[:, esquerda:direita + 1].mean(axis=1)
    base = fronteira(corpo, min(len(corpo) - 1, (fim_faixa + base0) // 2), 1, 2, LIMIAR_LINHA, base0)
    return esquerda, direita, topo, base


def preparar(imagem, pontos, expansao_x, expansao_y):
    janela, largura, altura = janela_retificada(imagem, pontos, expansao_x, expansao_y)
    altura_janela, largura_janela = janela.shape[:2]
    total_x, total_y = 1 + 2 * expansao_x, 1 + 2 * expansao_y
    esquerda0 = round(expansao_x / total_x * largura_janela)
    topo0 = round(expansao_y / total_y * altura_janela)
    inicial = (esquerda0, largura_janela - 1 - esquerda0, topo0, altura_janela - 1 - topo0)
    return {"janela": janela, "largura": largura, "altura": altura, "inicial": inicial,
            "expansao": (expansao_x, expansao_y), "classes": classificar(janela, *inicial)}


def validar_limites(contexto, novos, motivo, config):
    esquerda, direita, topo, base = novos
    esquerda0, direita0, topo0, base0 = contexto["inicial"]
    altura_janela, largura_janela = contexto["janela"].shape[:2]
    total_x, total_y = (1 + 2 * e for e in contexto["expansao"])
    nova_largura = (direita - esquerda + 1) / largura_janela * total_x * contexto["largura"]
    nova_altura = (base - topo + 1) / altura_janela * total_y * contexto["altura"]
    maximo = 2.6 if motivo == "faixa_acima" else 1.4
    if not 0.55 * contexto["largura"] <= nova_largura <= maximo * contexto["largura"]:
        return False
    if not 0.6 * contexto["altura"] <= nova_altura <= (maximo if motivo == "faixa_acima" else 1.6) * contexto["altura"]:
        return False
    if not config["razao_min"] <= nova_largura / nova_altura <= config["razao_max"]:
        return False
    largura_comum = max(0, min(direita, direita0) - max(esquerda, esquerda0) + 1)
    altura_comum = max(0, min(base, base0) - max(topo, topo0) + 1)
    if motivo == "bordas" and largura_comum * altura_comum / ((direita - esquerda + 1) * (base - topo + 1)) < 0.6:
        return False
    cinza = contexto["classes"][3]
    p10, p90 = np.percentile(cinza[topo:base + 1, esquerda:direita + 1], [10, 90])
    return p90 - p10 >= config["contraste_min"]


def converter(pontos, contexto, novos):
    esquerda, direita, topo, base = novos
    altura_janela, largura_janela = contexto["janela"].shape[:2]
    expansao_x, expansao_y = contexto["expansao"]
    s = [-expansao_x + coluna / largura_janela * (1 + 2 * expansao_x) for coluna in (esquerda, direita + 1)]
    t = [-expansao_y + linha / altura_janela * (1 + 2 * expansao_y) for linha in (topo, base + 1)]
    return quadrilatero(pontos, s[0], s[1], t[0], t[1])


def refinar(imagem, pontos, config):
    pontos = ordenar_pontos(pontos)
    contexto = preparar(imagem, pontos, config["expansao_largura"], config["expansao_altura"])
    if contexto["largura"] < 8 or contexto["altura"] < 4:
        return pontos, None
    neutro, faixa, tem_faixa, _ = contexto["classes"]
    if not tem_faixa:
        ampla = preparar(imagem, pontos, 1.3, 0.9)
        acima = faixa_acima(ampla["janela"], ampla["classes"][0], *ampla["inicial"], config)
        if acima is not None and validar_limites(ampla, acima, "faixa_acima", config):
            return converter(pontos, ampla, acima), "faixa_acima"
    novos = limites(neutro, faixa, tem_faixa, *contexto["inicial"])
    if novos is None or novos == contexto["inicial"] or not validar_limites(contexto, novos, "bordas", config):
        return pontos, None
    return converter(pontos, contexto, novos), "bordas"
