import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

from config import PADRAO, carregar_config, validar
from main import codigo_saida, executar, menu
from processamento.detector import medidas_geometricas, sobreposicao
from processamento.fluxo import processar, processar_lote
from processamento.imagem import carregar, escala_cinza, ordenar_pontos, retificar
from utils.arquivos import historico, listar_imagens, salvar_imagem, salvar_json

RAIZ = Path(__file__).resolve().parents[1]


class TestesPrograma(unittest.TestCase):
    def setUp(self):
        self.temporaria = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporaria.cleanup)
        self.pasta = Path(self.temporaria.name)
        self.config = PADRAO.copy()
        self.log = lambda texto: None

    def lisa(self, nome="lisa.png"):
        caminho = self.pasta / nome
        salvar_imagem(caminho, np.full((320, 480, 3), 80, np.uint8))
        return caminho

    def test_cinza_calcula_luminancia(self):
        pixels = np.array([[[0, 0, 255], [0, 255, 0], [255, 0, 0], [255, 255, 255]]], np.uint8)
        np.testing.assert_array_equal(escala_cinza(pixels), [[76, 150, 29, 255]])

    def test_cinza_nao_altera_original_e_aceita_fatia(self):
        imagem = np.full((8, 8, 3), (10, 80, 200), np.uint8)
        copia = imagem.copy()
        self.assertEqual(escala_cinza(imagem[::2, ::2]).shape, (4, 4))
        np.testing.assert_array_equal(imagem, copia)

    def test_cinza_rejeita_tipo_invalido(self):
        with self.assertRaises(ValueError):
            escala_cinza(np.zeros((10, 10), np.float64))

    def test_formatos_validos_e_caminhos_unicode(self):
        for extensao in ["jpg", "jpeg", "png", "JPG", "PNG"]:
            with self.subTest(extensao=extensao):
                p = self.pasta / f"veículo com espaço.{extensao}"
                Image.new("RGB", (120, 70), "white").save(p)
                self.assertEqual(carregar(p, self.config).shape, (70, 120, 3))

    def test_inexistente(self):
        with self.assertRaisesRegex(ValueError, "inexistente"):
            carregar(self.pasta / "ausente.jpg", self.config)

    def test_formato_nao_suportado(self):
        p = self.pasta / "foto.bmp"
        Image.new("RGB", (20, 20)).save(p)
        with self.assertRaisesRegex(ValueError, "Formato"):
            carregar(p, self.config)

    def test_corrompida(self):
        p = self.pasta / "quebrada.jpg"
        p.write_bytes(b"imagem quebrada")
        with self.assertRaises(ValueError):
            carregar(p, self.config)

    def test_jpeg_truncado(self):
        p = self.pasta / "cortada.jpg"
        Image.new("RGB", (120, 120)).save(p)
        p.write_bytes(p.read_bytes()[:-100])
        with self.assertRaises(ValueError):
            carregar(p, self.config)

    def test_png_checksum_invalido(self):
        p = self.lisa()
        dados = bytearray(p.read_bytes())
        dados[29] ^= 1
        p.write_bytes(dados)
        with self.assertRaises(ValueError):
            carregar(p, self.config)

    def test_conteudo_disfarcado(self):
        p = self.pasta / "gif.png"
        Image.new("RGB", (10, 10)).save(p, format="GIF")
        with self.assertRaises(ValueError):
            carregar(p, self.config)

    def test_limite_pixels(self):
        p = self.pasta / "grande.png"
        Image.new("RGB", (1100, 1000)).save(p)
        self.config["max_megapixels"] = 1
        with self.assertRaisesRegex(ValueError, "pixels"):
            carregar(p, self.config)

    def test_limite_bytes(self):
        p = self.pasta / "grande.jpg"
        p.write_bytes(b"x" * (1024 ** 2 + 1))
        self.config["max_arquivo_mb"] = 1
        with self.assertRaisesRegex(ValueError, "tamanho"):
            carregar(p, self.config)

    def test_png_sem_sobrescrita(self):
        p = self.lisa()
        original = p.read_bytes()
        with self.assertRaises(FileExistsError):
            salvar_imagem(p, np.zeros((5, 5, 3), np.uint8))
        self.assertEqual(p.read_bytes(), original)

    def test_configuracao_invalida(self):
        for chave, valor in [("gaussiano", 4), ("nota_min", float("nan")), ("lado_maximo", 400.5),
                             ("area_min", 0.5), ("canny_baixo", 200), ("nota_min", True)]:
            with self.subTest(chave=chave, valor=valor), self.assertRaises(ValueError):
                validar({**PADRAO, chave: valor})

    def test_configuracao_json_e_desconhecida(self):
        p = self.pasta / "config.json"
        salvar_json(p, {"nota_min": 0.7})
        self.assertEqual(carregar_config(p)["nota_min"], 0.7)
        p.write_text('{"inexistente": 1}')
        with self.assertRaises(ValueError):
            carregar_config(p)
        p.write_text('[]')
        with self.assertRaises(ValueError):
            carregar_config(p)
        self.assertEqual(PADRAO["nota_min"], 0.80)

    def test_geometria_e_intersecao(self):
        pontos = np.float32([[30, 20], [230, 20], [230, 100], [30, 100]])
        w, h, angulo = medidas_geometricas(pontos)
        self.assertAlmostEqual(w / h, 2.5)
        self.assertAlmostEqual(angulo, 0)
        np.testing.assert_array_equal(ordenar_pontos(pontos[[2, 0, 3, 1]]), pontos)
        self.assertEqual(sobreposicao([0, 0, 10, 10], [0, 0, 10, 10]), 1)
        self.assertEqual(sobreposicao([0, 0, 10, 10], [20, 20, 10, 10]), 0)

    def test_retificacao_de_quadrilatero(self):
        imagem = np.zeros((150, 300, 3), np.uint8)
        pontos = np.float32([[40, 30], [250, 40], [240, 110], [30, 100]])
        cv2.fillConvexPoly(imagem, pontos.astype(np.int32), (240, 240, 240))
        recorte = retificar(imagem, pontos)
        self.assertGreater(recorte.shape[1], recorte.shape[0])
        self.assertGreater(recorte[5:-5, 5:-5].mean(), 230)

    def test_sem_veiculo_e_intermediarias(self):
        p = self.lisa()
        resultado = processar(p, self.pasta / "saida", self.config, True, self.log)
        self.assertEqual(resultado["estado"], "NAO_ENCONTRADA")
        self.assertIsNone(resultado["placa"])
        destino = Path(resultado["pasta"])
        for nome in ["00_original", "01_cinza", "02_gaussiano", "04_bordas", "05_morfologia", "06_candidatos"]:
            self.assertTrue((destino / resultado["etapas"][nome]).is_file())
        self.assertTrue((destino / "resultado.json").is_file())

    def test_opcao_sem_intermediarias(self):
        resultado = processar(self.lisa(), self.pasta / "saida", self.config, False, self.log)
        self.assertEqual(resultado["etapas"], {})
        self.assertFalse((Path(resultado["pasta"]) / "intermediarias").exists())

    def test_falha_de_gravacao(self):
        p = self.lisa()
        saida = self.pasta / "obstaculo"
        saida.write_text("arquivo")
        resultado = processar(p, saida, self.config, False, self.log)
        self.assertEqual(resultado["estado"], "ERRO")

    def test_lote_continua_apos_falha_e_nao_sobrescreve(self):
        p = self.lisa()
        resultados = processar_lote([self.pasta / "ausente.jpg", p, p], self.pasta / "saida", self.config, False, self.log)
        self.assertEqual([r["estado"] for r in resultados], ["ERRO", "NAO_ENCONTRADA", "NAO_ENCONTRADA"])
        self.assertNotEqual(resultados[1]["pasta"], resultados[2]["pasta"])
        self.assertEqual(len(list((self.pasta / "saida/lotes").glob("*.json"))), 1)

    def test_listagem_recursiva_exclui_saida(self):
        self.lisa()
        self.lisa("sub/outra.png")
        self.lisa("saida/ignorada.png")
        saida = self.pasta / "saida"
        self.assertEqual(len(listar_imagens(self.pasta, saida)), 1)
        self.assertEqual(len(listar_imagens(self.pasta, saida, True)), 2)
        with self.assertRaises(ValueError):
            listar_imagens(self.pasta, self.pasta)
        with self.assertRaises(ValueError):
            processar_lote([], saida, self.config, log=self.log)

    def test_historico_ignora_relatorio_corrompido(self):
        processar(self.lisa(), self.pasta / "saida", self.config, False, self.log)
        ruim = self.pasta / "saida/ruim/resultado.json"
        ruim.parent.mkdir()
        ruim.write_text("quebrado")
        self.assertEqual(len(historico(self.pasta / "saida")), 1)

    def test_cli_codigos_de_saida(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(executar(["--imagem", str(self.lisa()), "--saida", str(self.pasta / "saida"), "--sem-intermediarias"]), 1)
            self.assertEqual(executar(["--imagem", str(self.pasta / "ausente.jpg")]), 2)
            self.assertEqual(executar(["--salvar-config", str(self.pasta / "config.json")]), 0)
        self.assertEqual(codigo_saida([{"estado": "ENCONTRADA"}]), 0)

    def test_cli_rejeita_argumentos_conflitantes(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as erro:
            executar(["--recursivo"])
        self.assertEqual(erro.exception.code, 2)

    def test_menu_todas_as_opcoes(self):
        entrada = RAIZ / "imagens/carros/img_003.jpg"
        lote = self.pasta / "lote"
        lote.mkdir()
        (lote / "carro.jpg").write_bytes(entrada.read_bytes())
        self.lisa("lote/sem_veiculo.png")
        comandos = ["6", "5", "4", "1", "n", "4", "1", "2", str(entrada), "s", "4", "1",
                    "3", str(lote), "n", "n", "5", "9", "0"]
        buffer = io.StringIO()
        with patch("builtins.input", side_effect=comandos), contextlib.redirect_stdout(buffer):
            self.assertEqual(menu(self.pasta / "saida", self.config), 0)
        texto = buffer.getvalue()
        for esperado in ["Configuração atual", "não salvou", "[ETAPA]", "RESUMO DO PROCESSAMENTO", "Opção inválida"]:
            self.assertIn(esperado, texto)
        self.assertEqual(len(historico(self.pasta / "saida")), 4)

    def test_menu_encerra_em_eof(self):
        with patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(menu(self.pasta, self.config), 0)

    def test_arquivos_reais_permanecem_inalterados(self):
        p = RAIZ / "imagens/carros/img_003.jpg"
        antes = hashlib.sha256(p.read_bytes()).hexdigest()
        resultado = processar(p, self.pasta, self.config, False, self.log)
        self.assertEqual(resultado["estado"], "ENCONTRADA")
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), antes)

    def test_fotografias_sem_veiculo(self):
        for nome in ["camera.png", "coffee.png", "astronaut.png", "grass.png"]:
            with self.subTest(arquivo=nome):
                resultado = processar(RAIZ / "imagens/sem_veiculo" / nome, self.pasta, self.config, False, self.log)
                self.assertEqual(resultado["estado"], "NAO_ENCONTRADA")

    def test_fotografia_real_com_variacoes(self):
        original = carregar(RAIZ / "imagens/carros/img_003.jpg", self.config)
        h, w = original.shape[:2]
        referencia = np.float32([[499, 810], [663, 810], [663, 893], [499, 893]])
        for variante in ["original", "escura", "pequena", "grande", "inclinada", "perspectiva", "cinza"]:
            with self.subTest(variante=variante):
                pontos = referencia.copy()
                if variante == "escura":
                    imagem = (original.astype(np.float32) * 0.32).astype(np.uint8)
                elif variante in {"pequena", "grande"}:
                    escala = 0.5 if variante == "pequena" else 2
                    imagem = cv2.resize(original, None, fx=escala, fy=escala)
                    pontos *= escala
                elif variante == "inclinada":
                    matriz = cv2.getRotationMatrix2D((w / 2, h / 2), 12, 1)
                    imagem = cv2.warpAffine(original, matriz, (w, h))
                    pontos = cv2.transform(pontos[None], matriz)[0]
                elif variante == "perspectiva":
                    origem = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
                    destino = np.float32([[w * 0.08, h * 0.03], [w * 0.95, 0], [w - 1, h - 1], [0, h * 0.95]])
                    matriz = cv2.getPerspectiveTransform(origem, destino)
                    imagem = cv2.warpPerspective(original, matriz, (w, h))
                    pontos = cv2.perspectiveTransform(pontos[None], matriz)[0]
                elif variante == "cinza":
                    imagem = cv2.cvtColor(escala_cinza(original), cv2.COLOR_GRAY2BGR)
                else:
                    imagem = original.copy()
                caminho = self.pasta / f"{variante}.png"
                salvar_imagem(caminho, imagem)
                resultado = processar(caminho, self.pasta / "saida", self.config, False, self.log)
                self.assertEqual(resultado["estado"], "ENCONTRADA", resultado["mensagem"])
                r = resultado["regiao"]
                detectada = [r[k] for k in ["x", "y", "largura", "altura"]]
                minimo, maximo = pontos.min(axis=0), pontos.max(axis=0)
                esperada = [*minimo, *(maximo - minimo)]
                self.assertGreaterEqual(sobreposicao(esperada, detectada), 0.5)
                placa = carregar(Path(resultado["pasta"]) / resultado["placa"], self.config)
                self.assertGreater(placa.shape[1], placa.shape[0])

    def test_configuracao_valida_parametros_do_refinamento(self):
        for nome, valor in [("razao_preferida", 6.0), ("refinar_bordas", 2), ("expansao_largura", 0.9)]:
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    validar({**PADRAO, nome: valor})

    def test_refinamento_incorpora_faixa_acima_do_corpo(self):
        caminho = RAIZ / "imagens" / "novas" / "img_031.jpg"
        referencia = [350, 652, 133, 70]
        com = processar(caminho, self.pasta / "com", self.config, False, self.log)
        sem = processar(caminho, self.pasta / "sem", {**self.config, "refinar_bordas": 0}, False, self.log)
        caixa_com = [com["regiao"][k] for k in ["x", "y", "largura", "altura"]]
        caixa_sem = [sem["regiao"][k] for k in ["x", "y", "largura", "altura"]]
        self.assertEqual(com["regiao"]["refinamento"], "faixa_acima")
        self.assertIsNone(sem["regiao"]["refinamento"])
        self.assertLess(sobreposicao(referencia, caixa_sem), 0.5)
        self.assertGreaterEqual(sobreposicao(referencia, caixa_com), 0.7)


if __name__ == "__main__":
    unittest.main()
