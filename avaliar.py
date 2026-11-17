import argparse
import csv
import uuid
from pathlib import Path

from config import carregar_config
from processamento.detector import sobreposicao
from processamento.fluxo import processar
from utils.arquivos import salvar_json


def avaliar(pasta, referencias, saida, config, log=print):
    with Path(referencias).open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames != ["arquivo", "x", "y", "largura", "altura"]:
            raise ValueError("Cabeçalho esperado: arquivo,x,y,largura,altura.")
        anotacoes = list(leitor)
    if not anotacoes:
        raise ValueError("Não há referências no CSV.")
    for linha in anotacoes:
        linha["caixa"] = [int(linha[n]) for n in ["x", "y", "largura", "altura"]]
        x, y, w, h = linha["caixa"]
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            raise ValueError("Caixa de referência inválida.")
        if Path(linha["arquivo"]).name != linha["arquivo"]:
            raise ValueError("Use apenas nomes de arquivos na referência.")
    linhas = []
    for linha in anotacoes:
        resultado = processar(Path(pasta) / linha["arquivo"], saida, config, False, log)
        regiao = resultado["regiao"]
        detectada = [regiao[k] for k in ["x", "y", "largura", "altura"]] if regiao else [0, 0, 0, 0]
        iou = sobreposicao(linha["caixa"], detectada)
        linhas.append({"arquivo": linha["arquivo"], "estado": resultado["estado"],
                       "iou": round(iou, 6), "localizada": resultado["estado"] == "ENCONTRADA" and iou >= 0.5,
                       "ref_x": linha["caixa"][0], "ref_y": linha["caixa"][1],
                       "ref_largura": linha["caixa"][2], "ref_altura": linha["caixa"][3],
                       "det_x": detectada[0], "det_y": detectada[1],
                       "det_largura": detectada[2], "det_altura": detectada[3]})
        log(f'[AVALIAÇÃO] {linha["arquivo"]}: IoU {iou:.3f}')
    destino = Path(saida).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    nome = "avaliacao_" + uuid.uuid4().hex[:8]
    with (destino / f"{nome}.csv").open("x", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=linhas[0].keys())
        escritor.writeheader()
        escritor.writerows(linhas)
    resumo = {"total": len(linhas), "localizadas": sum(l["localizada"] for l in linhas),
              "falhas_execucao": sum(l["estado"] == "ERRO" for l in linhas),
              "criterio": "IoU >= 0.50", "configuracao": config, "resultados": linhas}
    salvar_json(destino / f"{nome}.json", resumo)
    log(f'[AVALIAÇÃO] {resumo["localizadas"]}/{resumo["total"]} localizadas; {resumo["falhas_execucao"]} erros de execução.')
    log(f"[ARQUIVO] {destino / (nome + '.csv')}")
    return resumo


def executar():
    parser = argparse.ArgumentParser(description="Avalia as caixas detectadas contra referências manuais.")
    parser.add_argument("--pasta", type=Path, required=True)
    parser.add_argument("--referencias", type=Path, required=True)
    parser.add_argument("--saida", type=Path, default=Path("resultados/avaliacao"))
    parser.add_argument("--config", type=Path)
    opcoes = parser.parse_args()
    try:
        resumo = avaliar(opcoes.pasta, opcoes.referencias, opcoes.saida, carregar_config(opcoes.config))
        return 2 if resumo["falhas_execucao"] else int(resumo["localizadas"] != resumo["total"])
    except (ValueError, OSError) as erro:
        print(f"[ERRO] {erro}")
        return 2


if __name__ == "__main__":
    raise SystemExit(executar())
