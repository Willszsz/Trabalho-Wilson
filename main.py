import argparse
import json
from pathlib import Path

from config import PADRAO, carregar_config
from processamento.fluxo import processar, processar_lote
from utils.arquivos import historico, listar_imagens, salvar_json

RAIZ = Path(__file__).resolve().parent


def perguntar(texto):
    return input(texto).strip().strip('"')


def guardar_etapas():
    return perguntar("Salvar imagens intermediárias? [S/n]: ").lower() != "n"


def mostrar_historico(pasta):
    registros = historico(pasta)
    if not registros:
        print("[INFO] Nenhum resultado anterior disponível.")
    for indice, item in enumerate(registros, 1):
        print(f'[{indice}] {Path(item["arquivo"]).name} | {item["estado"]}')
        print(f'    Relatório: {item["relatorio"]}')
    return registros


def mostrar_etapas(pasta):
    registros = mostrar_historico(pasta)
    if not registros:
        return
    numero = int(perguntar("Número do resultado para consultar: "))
    if not 1 <= numero <= len(registros):
        raise ValueError("Número de resultado inválido.")
    item = registros[numero - 1]
    etapas = item.get("etapas", {})
    if not etapas:
        print("[INFO] Esta execução não salvou imagens intermediárias.")
    for etapa, caminho in etapas.items():
        completo = Path(item["relatorio"]).parent / caminho
        estado = "salvo" if completo.is_file() else "arquivo ausente"
        print(f"[ETAPA] {etapa}: {completo} ({estado})")


def informacoes(config):
    print("\nAlgoritmo clássico: cinza por NumPy, Gaussiano, CLAHE, Canny e morfologia.")
    print("Propostas por contornos, faixas de cor e traços escuros. Seleção por geometria e textura.")
    print("O recorte usa os pixels originais e pode corrigir inclinação e pequenas deformações de perspectiva.")
    print("Antes do recorte, as bordas são refinadas pela estrutura da placa: faixa colorida em cima e corpo claro embaixo.")
    print("Sem OCR ou modelos de IA. A pontuação não é uma probabilidade; podem ocorrer erros.")
    print("Configuração atual (use --config arquivo.json para alterar):")
    print(json.dumps(config, indent=2, ensure_ascii=False))


def menu(pasta, config):
    while True:
        print("\n===============================================\nEGYPTIAN LICENSE PLATE EXTRACTOR")
        print("Sistema de detecção e extração de placas.\n")
        print("[1] Testar imagem de exemplo\n[2] Processar imagem personalizada")
        print("[3] Processar todas as imagens de uma pasta\n[4] Consultar etapas do processamento")
        print("[5] Consultar resultados anteriores\n[6] Informações do algoritmo\n[0] Sair")
        try:
            opcao = perguntar("Escolha uma opção: ")
            if opcao == "0":
                return 0
            if opcao == "1":
                processar(RAIZ / "imagens/carros/img_003.jpg", pasta, config, guardar_etapas())
            elif opcao == "2":
                entrada = perguntar("Caminho da imagem: ")
                if not entrada:
                    raise ValueError("Caminho não informado.")
                processar(Path(entrada), pasta, config, guardar_etapas())
            elif opcao == "3":
                entrada = perguntar("Pasta das imagens: ")
                if not entrada:
                    raise ValueError("Pasta não informada.")
                recursivo = perguntar("Incluir subpastas? [s/N]: ").lower() == "s"
                salvar = guardar_etapas()
                entradas = listar_imagens(entrada, pasta, recursivo)
                processar_lote(entradas, pasta, config, salvar)
            elif opcao == "4":
                mostrar_etapas(pasta)
            elif opcao == "5":
                mostrar_historico(pasta)
            elif opcao == "6":
                informacoes(config)
            else:
                print("[ERRO] Opção inválida.")
        except (ValueError, OSError) as erro:
            print(f"[ERRO] {erro}")
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Encerrado.")
            return 0


def codigo_saida(resultados):
    estados = {r["estado"] for r in resultados}
    return 2 if "ERRO" in estados else 1 if "NAO_ENCONTRADA" in estados else 0


def executar(argumentos=None):
    parser = argparse.ArgumentParser(description="Detecta e extrai placas egípcias sem OCR.")
    entrada = parser.add_mutually_exclusive_group()
    entrada.add_argument("--imagem", type=Path)
    entrada.add_argument("--pasta", type=Path)
    entrada.add_argument("--exemplo", action="store_true")
    entrada.add_argument("--salvar-config", type=Path)
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--recursivo", action="store_true")
    salvar = parser.add_mutually_exclusive_group()
    salvar.add_argument("--intermediarias", dest="intermediarias", action="store_true")
    salvar.add_argument("--sem-intermediarias", dest="intermediarias", action="store_false")
    parser.set_defaults(intermediarias=True)
    opcoes = parser.parse_args(argumentos)
    if opcoes.recursivo and not opcoes.pasta:
        parser.error("--recursivo exige --pasta.")
    try:
        config = carregar_config(opcoes.config)
        if opcoes.salvar_config:
            salvar_json(opcoes.salvar_config, config)
            print(f"[OK] Configuração salva em {opcoes.salvar_config}")
            return 0
        if opcoes.pasta:
            entradas = listar_imagens(opcoes.pasta, opcoes.saida, opcoes.recursivo)
            resultados = processar_lote(entradas, opcoes.saida, config, opcoes.intermediarias)
            return codigo_saida(resultados)
        if opcoes.imagem or opcoes.exemplo:
            entrada = opcoes.imagem or RAIZ / "imagens/carros/img_003.jpg"
            return codigo_saida([processar(entrada, opcoes.saida, config, opcoes.intermediarias)])
        return menu(opcoes.saida, config)
    except (ValueError, OSError) as erro:
        print(f"[ERRO] {erro}")
        return 2
    except KeyboardInterrupt:
        print("\n[INFO] Processamento interrompido. A pasta pode conter arquivos parciais.")
        return 130


if __name__ == "__main__":
    raise SystemExit(executar())
