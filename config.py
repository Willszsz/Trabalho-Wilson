import json
import math
from pathlib import Path

PADRAO = {
    "lado_maximo": 1400,
    "max_megapixels": 40,
    "max_arquivo_mb": 50,
    "gaussiano": 3,
    "contraste_local": 2.0,
    "canny_baixo": 45,
    "canny_alto": 135,
    "fechamento_x": 0.012,
    "fechamento_y": 0.003,
    "razao_min": 1.3,
    "razao_max": 5.5,
    "area_min": 0.00045,
    "area_max": 0.22,
    "largura_min": 32,
    "altura_min": 12,
    "inclinacao_max": 35,
    "saturacao_min": 85,
    "brilho_cor_min": 45,
    "contraste_min": 20,
    "bordas_min": 0.035,
    "bordas_max": 0.48,
    "marcas_min": 3,
    "ocupacao_min": 0.38,
    "nota_min": 0.80,
    "razao_preferida": 2.3,
    "margem": 0.035,
    "refinar_bordas": 1,
    "expansao_largura": 0.2,
    "expansao_altura": 0.35,
    "limite_contornos": 8000,
}

LIMITES = {
    "lado_maximo": (320, 3000), "max_megapixels": (1, 60),
    "max_arquivo_mb": (1, 200), "gaussiano": (1, 15),
    "contraste_local": (0.1, 8), "canny_baixo": (1, 254),
    "canny_alto": (2, 255), "fechamento_x": (0.001, 0.08),
    "fechamento_y": (0.001, 0.04), "razao_min": (1, 6),
    "razao_max": (1.1, 10), "area_min": (0.00001, 0.1),
    "area_max": (0.001, 0.8), "largura_min": (12, 400),
    "altura_min": (6, 200), "inclinacao_max": (0, 70),
    "saturacao_min": (0, 255), "brilho_cor_min": (0, 255),
    "contraste_min": (1, 150), "bordas_min": (0.001, 0.4),
    "bordas_max": (0.1, 0.95), "marcas_min": (1, 15),
    "ocupacao_min": (0.1, 0.9), "nota_min": (0, 1),
    "margem": (0, 0.15), "limite_contornos": (100, 30000),
    "razao_preferida": (1, 6), "refinar_bordas": (0, 1),
    "expansao_largura": (0, 0.5), "expansao_altura": (0, 0.8),
}


def validar(config):
    if set(config) != set(PADRAO):
        raise ValueError("A configuração contém parâmetros ausentes ou desconhecidos.")
    for nome, valor in config.items():
        minimo, maximo = LIMITES[nome]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"{nome}: informe um número.")
        if not math.isfinite(valor) or not minimo <= valor <= maximo:
            raise ValueError(f"{nome}: use um valor entre {minimo} e {maximo}.")
        if isinstance(PADRAO[nome], int) and not isinstance(valor, int):
            raise ValueError(f"{nome}: informe um número inteiro.")
    if config["gaussiano"] % 2 == 0:
        raise ValueError("gaussiano precisa ser ímpar.")
    for menor, maior in [("razao_min", "razao_max"), ("area_min", "area_max"),
                         ("bordas_min", "bordas_max"), ("canny_baixo", "canny_alto")]:
        if config[menor] >= config[maior]:
            raise ValueError(f"{menor} precisa ser menor que {maior}.")
    if not config["razao_min"] <= config["razao_preferida"] <= config["razao_max"]:
        raise ValueError("razao_preferida precisa estar entre razao_min e razao_max.")
    return config


def carregar_config(caminho=None):
    config = PADRAO.copy()
    if caminho:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        if not isinstance(dados, dict):
            raise ValueError("A configuração precisa ser um objeto JSON.")
        desconhecidos = set(dados) - set(config)
        if desconhecidos:
            raise ValueError(f"Parâmetros desconhecidos: {', '.join(sorted(desconhecidos))}")
        config.update(dados)
    return validar(config)
