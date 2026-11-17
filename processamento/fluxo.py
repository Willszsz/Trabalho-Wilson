import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from config import validar
from processamento.bordas import detectar_bordas
from processamento.detector import caixa, detectar
from processamento.filtros import morfologia, realcar, suavizar
from processamento.imagem import carregar, escala_cinza, reduzir, retificar
from processamento.refinamento import refinar
from utils.arquivos import criar_destino, salvar_imagem, salvar_json


def registrar_etapa(destino, nome, imagem, intermediarias, etapas):
    if intermediarias:
        caminho = destino / "intermediarias" / f"{nome}.png"
        salvar_imagem(caminho, imagem)
        etapas[nome] = str(caminho.relative_to(destino))


def processar(entrada, pasta, config, intermediarias=True, log=print):
    inicio = time.perf_counter()
    entrada = Path(entrada)
    resultado = {"arquivo": str(entrada.resolve()), "estado": "ERRO", "mensagem": "",
                 "dimensoes": None, "regiao": None, "placa": None, "pasta": None,
                 "etapas": {}, "candidatos": [], "configuracao": config.copy()}
    destino = None
    log(f"\n[INFO] Arquivo selecionado: {entrada}")
    try:
        validar(config)
        original = carregar(entrada, config)
        altura, largura = original.shape[:2]
        resultado["dimensoes"] = {"largura": largura, "altura": altura}
        log(f"[OK] Imagem carregada. Dimensões: {largura} x {altura} pixels.")
        destino = criar_destino(pasta, entrada)
        resultado["pasta"] = str(destino)
        registrar_etapa(destino, "00_original", original, intermediarias, resultado["etapas"])
        trabalho = reduzir(original, config["lado_maximo"])
        resultado["dimensoes_trabalho"] = {"largura": trabalho.shape[1], "altura": trabalho.shape[0]}
        log("[1/6] Convertendo para escala de cinza...")
        cinza = escala_cinza(trabalho)
        registrar_etapa(destino, "01_cinza", cinza, intermediarias, resultado["etapas"])
        log("[OK] Conversão concluída.")
        log("[2/6] Aplicando filtro Gaussiano e realce de contraste...")
        filtrada = suavizar(cinza, config)
        contraste = realcar(filtrada, config)
        registrar_etapa(destino, "02_gaussiano", filtrada, intermediarias, resultado["etapas"])
        registrar_etapa(destino, "03_contraste", contraste, intermediarias, resultado["etapas"])
        log("[OK] Filtro e realce concluídos.")
        log("[3/6] Detectando bordas...")
        bordas = detectar_bordas(contraste, config)
        registrar_etapa(destino, "04_bordas", bordas, intermediarias, resultado["etapas"])
        log("[OK] Detecção de bordas concluída.")
        log("[4/6] Aplicando operações morfológicas...")
        mapa = morfologia(bordas, config)
        registrar_etapa(destino, "05_morfologia", mapa, intermediarias, resultado["etapas"])
        log("[OK] Morfologia concluída.")
        log("[5/6] Analisando regiões candidatas...")
        escolhida, candidatas, mapas, limitado = detectar(trabalho, contraste, bordas, mapa, config)
        resultado["candidatos"] = candidatas
        resultado["limite_contornos_atingido"] = limitado
        for nome, imagem in mapas.items():
            registrar_etapa(destino, nome, imagem, intermediarias, resultado["etapas"])
        visualizacao = trabalho.copy()
        for candidata in candidatas[:30]:
            pontos = np.rint(candidata["pontos"]).astype(np.int32)
            cv2.polylines(visualizacao, [pontos], True, (0, 180, 255), 2)
            cv2.putText(visualizacao, f'{candidata["nota"]:.2f}', tuple(pontos[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        registrar_etapa(destino, "06_candidatos", visualizacao, intermediarias, resultado["etapas"])
        log(f"[OK] Análise concluída: {len(candidatas)} candidatas após os filtros.")
        if limitado:
            log("[AVISO] Limite de contornos atingido; foram analisados os maiores.")
        anotada = original.copy()
        if escolhida is None:
            resultado["estado"] = "NAO_ENCONTRADA"
            resultado["mensagem"] = "Nenhuma placa foi identificada nesta imagem."
            log("[6/6] Extração não realizada: nenhuma região atingiu os critérios.")
        else:
            log("[6/6] Extraindo placa...")
            pontos = np.asarray(escolhida["pontos"], dtype=np.float32)
            pontos = (pontos * np.array([largura / trabalho.shape[1], altura / trabalho.shape[0]])).astype(np.float32)
            refino = None
            if config["refinar_bordas"]:
                pontos, refino = refinar(original, pontos, config)
                log("[OK] Bordas refinadas." if refino == "bordas" else
                    "[OK] Faixa superior incorporada: a região inicial continha apenas o corpo da placa." if refino == "faixa_acima" else
                    "[INFO] Bordas mantidas: o refinamento não encontrou limites mais confiáveis.")
            centro = pontos.mean(axis=0)
            pontos = centro + (pontos - centro) * (1 + 2 * config["margem"])
            pontos = np.clip(pontos, [0, 0], [largura - 1, altura - 1]).astype(np.float32)
            placa = retificar(original, pontos)
            caminho = destino / "placas" / "placa.png"
            salvar_imagem(caminho, placa)
            cv2.polylines(anotada, [np.rint(pontos).astype(np.int32)], True, (0, 255, 0), max(2, largura // 500))
            x, y, w, h = caixa(pontos, original.shape)
            resultado["regiao"] = {"x": x, "y": y, "largura": w, "altura": h,
                                   "pontos": pontos.tolist(), "nota": escolhida["nota"], "origem": escolhida["origem"],
                                   "refinamento": refino}
            resultado["placa"] = str(caminho.relative_to(destino))
            resultado["estado"] = "ENCONTRADA"
            resultado["mensagem"] = "Região mais provável extraída. Pontuação heurística, não probabilidade."
            log(f"[OK] Extração concluída. X: {x} | Y: {y} | Largura: {w} | Altura: {h}")
            log(f"[ARQUIVO] {caminho}")
        caminho = destino / "processadas" / "resultado.png"
        salvar_imagem(caminho, anotada)
        resultado["processada"] = str(caminho.relative_to(destino))
        resultado["tempo_segundos"] = round(time.perf_counter() - inicio, 4)
        salvar_json(destino / "resultado.json", resultado)
        log("[RESULTADO] " + ("Placa identificada: SIM." if escolhida is not None else resultado["mensagem"]))
        log(f'[TEMPO] {resultado["tempo_segundos"]:.3f} segundos.')
        log(f"[ARQUIVOS] {destino}")
    except (OSError, ValueError, cv2.error) as erro:
        resultado.update(estado="ERRO", mensagem=str(erro), regiao=None, placa=None)
        resultado["tempo_segundos"] = round(time.perf_counter() - inicio, 4)
        log(f"[ERRO] {entrada.name}: {erro}")
        if destino is not None and not (destino / "resultado.json").exists():
            try:
                salvar_json(destino / "resultado.json", resultado)
            except (OSError, ValueError) as falha:
                log(f"[ERRO] Não foi possível salvar o relatório: {falha}")
    return resultado


def processar_lote(entradas, pasta, config, intermediarias=True, log=print):
    if not entradas:
        raise ValueError("Nenhuma imagem JPG, JPEG ou PNG foi encontrada.")
    resultados = []
    for indice, entrada in enumerate(entradas, 1):
        log(f"\n[LOTE] {indice}/{len(entradas)}")
        resultados.append(processar(entrada, pasta, config, intermediarias, log))
    contagem = {estado: sum(r["estado"] == estado for r in resultados)
                for estado in ["ENCONTRADA", "NAO_ENCONTRADA", "ERRO"]}
    resumo = {"total": len(resultados), "contagem": contagem, "resultados": resultados}
    destino = Path(pasta).resolve() / "lotes" / f"lote_{uuid.uuid4().hex[:12]}.json"
    salvar_json(destino, resumo)
    log("\n===============================================\nRESUMO DO PROCESSAMENTO")
    log(f'Total: {len(resultados)} | Identificadas: {contagem["ENCONTRADA"]} | '
        f'Não identificadas: {contagem["NAO_ENCONTRADA"]} | Falhas: {contagem["ERRO"]}')
    log(f"[ARQUIVO] {destino}")
    return resultados
