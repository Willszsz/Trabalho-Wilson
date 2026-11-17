# Egyptian License Plate Extractor (Python)

**Download:** [projeto completo em ZIP](https://github.com/Victornck/EgyptianPlateExtractorPython/archive/refs/heads/main.zip). Extraia a pasta, instale `requirements.txt` e execute `python main.py`. O ZIP inclui código, fotografias, testes e documentação. A versão 1.0.0 continua disponível na tag `v1.0.0`.

Implementação independente em Python para localizar e recortar placas automotivas egípcias. Usa processamento clássico de imagens, OpenCV e NumPy. Não usa OCR, reconhecimento de marcas, redes neurais ou modelos treinados.

O programa funciona pelo terminal, com menu e comandos diretos. Código, fotografias, testes e evidências estão incluídos. Não depende da versão Java, do Maven ou de um JAR.

## Instalação e execução

Requer **Python 3.11 a 3.14, de 64 bits**. Os testes desta versão passaram em Python 3.11.18, 3.12.16, 3.13.18 e 3.14.10, em Linux x64. Windows não foi executado neste ambiente. Python 3.10 não é mais suportado, porque o NumPy 2.3 exige 3.11 ou superior.

Extraia o ZIP e abra o terminal na pasta em que estão `main.py` e `requirements.txt`.

```text
pip install -r requirements.txt
python main.py
```

Se houver mais de um Python instalado, use `python -m pip install -r requirements.txt` para instalar no mesmo interpretador que executará o programa. É necessário acesso à internet para instalar as dependências pela primeira vez. Depois, a execução do detector é local.

Ambiente virtual recomendado no Windows 11, sem necessidade de alterar a política do PowerShell (troque `3.12` pela versão instalada, de 3.11 a 3.14):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

No Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

No menu, selecione **1** para processar uma fotografia real já incluída. O programa pergunta se deve salvar as imagens intermediárias. Para outra foto, use **2** e informe seu caminho; caminhos com espaços e acentos são aceitos. Caminhos relativos informados pelo usuário partem da pasta atual do terminal. A foto de exemplo e a pasta padrão de resultados são localizadas em relação a `main.py`.

No Windows, `executar.bat` inicia o programa depois da instalação das dependências. Ele utiliza `.venv` quando disponível; caso contrário, utiliza `python` do PATH. Para desenvolvimento, qualquer editor ou terminal com o mesmo ambiente virtual pode ser usado.

## Menu completo

| Opção | Operação |
|---|---|
| 1 | Processa `imagens/carros/img_003.jpg` |
| 2 | Processa uma imagem informada pelo usuário |
| 3 | Processa as imagens de uma pasta, com inclusão opcional de subpastas |
| 4 | Lista resultados e mostra os caminhos das etapas salvas de uma execução escolhida |
| 5 | Lista resultados anteriores e seus relatórios |
| 6 | Explica o algoritmo e mostra a configuração atual |
| 0 | Encerra |

Todas as opções foram exercitadas nos testes. A consulta de etapas mostra arquivos em disco e não abre janelas gráficas. Caso as intermediárias tenham sido desativadas, a consulta informa essa condição. O histórico considera relatórios `*/resultado.json` dentro da pasta de saída escolhida.

## Comandos diretos

```text
python main.py --exemplo
python main.py --imagem imagens/carros/img_003.jpg --sem-intermediarias
python main.py --pasta imagens/carros --saida resultados/lote --sem-intermediarias
python main.py --pasta imagens/carros --recursivo --intermediarias
python main.py --imagem imagens/carros/img_003.jpg --config config_exemplo.json
python main.py --salvar-config minha_config.json
python main.py --help
```

O modo não interativo salva intermediárias por padrão; use `--sem-intermediarias` para desligar. A configuração JSON pode conter apenas os parâmetros que deseja alterar. Parâmetros desconhecidos, valores fora do intervalo, números não finitos e kernels pares são rejeitados. `--salvar-config` não sobrescreve um arquivo existente.

Códigos de saída: **0** = todas as entradas processadas tiveram uma região selecionada, ou o menu/comando de manutenção encerrou normalmente; **1** = alguma imagem válida sem detecção; **2** = erro de entrada, configuração ou processamento; **130** = interrupção do processamento por Ctrl+C no modo direto. No menu, os resultados aparecem a cada operação e sair normalmente retorna 0. Em lote, erro tem prioridade sobre ausência de placa.

## Resultados

Cada imagem recebe um diretório exclusivo com nome, data/hora local e identificador aleatório. Repetir uma execução não sobrescreve a anterior.

```text
resultados/
  img_003_DATA_HORA_ID/
    resultado.json
    placas/placa.png
    processadas/resultado.png
    intermediarias/
      00_original.png
      01_cinza.png
      02_gaussiano.png
      03_contraste.png
      04_bordas.png
      05_morfologia.png
      06_candidatos.png
      faixas.png
      textura.png
  lotes/lote_ID.json
```

A pasta `placas` só é criada quando há extração. `processadas/resultado.png` usa a resolução original e mostra a região selecionada em verde. As intermediárias usam a resolução de trabalho, exceto `00_original.png`, que preserva os pixels da fotografia decodificada. A entrada não é regravada.

`resultado.json` registra estado, dimensões, tempo medido, configuração, candidatas, medidas e região escolhida. Candidatas usam coordenadas da imagem de trabalho; `regiao` usa coordenadas da imagem original. `x`, `y`, `largura` e `altura` representam a caixa envolvente; `pontos` descreve o quadrilátero usado no recorte. A imagem de candidatos mostra até 30 propostas para não ficar ilegível; o relatório contém todas as propostas que passaram pelos filtros e pela supressão de duplicatas.

O tempo cobre leitura, processamento e gravação das imagens, até imediatamente antes da gravação final do relatório. As mensagens de sucesso são emitidas depois de executar a etapa correspondente. Uma falha de escrita gera `ERRO`, não sucesso; uma execução interrompida pode deixar uma pasta parcial.

## Organização

```text
main.py                  Menu e argumentos de terminal
config.py                Parâmetros e validação
avaliar.py               Avaliação contra caixas de referência
processamento/
  imagem.py              Validação, leitura, cinza e recorte geométrico
  filtros.py             Gaussiano, contraste, morfologia e textura escura
  bordas.py              Canny
  detector.py            Propostas, geometria, textura e seleção
  refinamento.py         Ajuste das bordas da região escolhida
  fluxo.py               Sequência das etapas e processamento em lote
utils/arquivos.py        Diretórios, gravação, listagem e histórico
tests/test_programa.py   Testes com unittest
imagens/carros/          20 fotografias conhecidas para demonstração/comparação
imagens/reservadas/      10 fotografias separadas para avaliação da versão 1.0.0
imagens/novas/           20 fotografias incluídas na versão 1.1.0
imagens/sem_veiculo/     4 fotografias negativas
docs/                    Referências, métricas, fontes e evidências
```

Não há classes de produção, comentários ou docstrings nos arquivos Python. As funções usam dicionários, listas e matrizes NumPy. A classe de testes utiliza a estrutura padrão de `unittest`.

## Técnicas utilizadas

1. **Validação e leitura:** `pathlib` valida existência, extensão e bytes. Pillow verifica o conteúdo, dimensões e integridade antes da decodificação BGR pelo OpenCV. Pillow é usado para essa verificação, não como detector. GIF disfarçado de PNG é rejeitado. Limites configuráveis evitam entradas excessivamente grandes.
2. **Escala de trabalho:** o maior lado é limitado, preservando proporções. A extração final usa a imagem original. Fotos pequenas não são ampliadas nesta etapa.
3. **Cinza próprio:** operações vetorizadas calculam `Y = round(0,114 B + 0,587 G + 0,299 R)` com NumPy. A conversão principal não usa `cv2.cvtColor`.
4. **Ruído e contraste:** Gaussiano suaviza ruído; CLAHE realça contraste local para ajudar em iluminação irregular. As duas imagens são salvas separadamente quando solicitado.
5. **Bordas e morfologia:** Canny localiza transições e fechamento morfológico conecta traços próximos.
6. **Propostas complementares:** contornos de bordas, regiões claras por Otsu, faixas saturadas por grupos de tonalidade e agrupamentos de textura escura gerados por black-hat/Sobel. Regiões que aparentam representar apenas o corpo da placa também geram uma hipótese expandida para incluir o cabeçalho.
7. **Análise própria:** dimensões, proporção, área relativa, inclinação, distribuição horizontal dos traços e ocupação dos componentes internos filtram e ordenam as regiões. Componentes escuros são avaliados por forma; seus caracteres não são interpretados.
8. **Seleção:** a pontuação combina geometria, quantidade/distribuição de marcas, contraste, densidade de bordas, fundo e uma faixa colorida opcional. Candidatas sobrepostas são reduzidas; a melhor precisa superar `nota_min`. A pontuação não é uma probabilidade.
9. **Refinamento de bordas (implementação própria):** uma janela ampliada em torno da região escolhida é retificada a partir da imagem original. Cada pixel é classificado com NumPy como corpo claro neutro ou cor da faixa, com o matiz dominante estimado na própria região. Uma coluna só pertence à placa se tiver cor da faixa em cima e corpo claro embaixo; o topo é procurado no perfil da faixa e a base no perfil do corpo. Quando a região não tem faixa no topo, mas há uma faixa do mesmo matiz logo acima dela, a região era só o corpo da placa e passa a incluir a faixa. Sem fronteira confiável, a região original é mantida e o terminal informa isso. `refinar_bordas: 0` desativa a etapa.
10. **Recorte:** quando um contorno convexo fornece quatro cantos, esses pontos podem representar pequenas deformações de perspectiva. Nos demais casos, usa-se um retângulo orientado. Uma transformação geométrica retifica a região, acrescentando a margem configurada.

O lote é sequencial, continua após erros individuais e exclui a pasta de saída da seleção. Só JPG/JPEG/PNG entram na listagem automática. Uma pasta vazia produz mensagem de erro. A lista é construída antes de processar, evitando que as próprias saídas sejam selecionadas no mesmo lote.

## Ajuste de parâmetros

Consulte [CONFIGURACAO.md](docs/CONFIGURACAO.md). Os valores atuais estão em `config_exemplo.json`. Exemplo de configuração parcial:

```json
{
  "lado_maximo": 1600,
  "nota_min": 0.82,
  "canny_baixo": 40,
  "canny_alto": 130
}
```

Primeiro examine as intermediárias. Se detalhes pequenos desaparecerem, reveja a resolução de trabalho e os tamanhos mínimos. Se regiões se unirem, reduza o fechamento. Se as bordas sumirem, reveja contraste e limiares. Diminuir a nota mínima pode recuperar placas difíceis, mas aumenta falsos positivos. Não calibre apenas com fotografias positivas.

## Testes e avaliação real

```text
python -m unittest discover -v
python avaliar.py --pasta imagens/reservadas --referencias docs/referencias-python.csv --saida resultados/avaliacao
python avaliar.py --pasta imagens/carros --referencias docs/referencias-comparacao.csv --saida resultados/comparacao
python avaliar.py --pasta imagens/novas --referencias docs/referencias-novas.csv --saida resultados/novas
```

**32 testes automatizados passaram** em Python 3.11, 3.12, 3.13 e 3.14, incluindo subcasos com arquivos inválidos, execução de todas as opções do menu, iluminação, duas resoluções, inclinação, perspectiva, ausência de cor e o refinamento de bordas. Não se trata de 32 veículos distintos.

Resultados da versão 1.1.0: **10/10** nas reservadas `img_021` a `img_030` (IoU médio 0,837), **10/10** em `img_011` a `img_020` (0,808) e **15/15** em `img_036` a `img_050` (0,845), pelo critério IoU ≥ 0,50. No lote das 50 fotografias, todas produziram um recorte com a placa. As quatro fotografias sem veículo não produziram detecções; elas participaram da calibração do limiar na 1.0.0, então isso não é uma estimativa independente de falsos positivos.

Consulte [VALIDACAO.md](docs/VALIDACAO.md), com dados medidos, comparação descritiva com Java, imagens e limitações. IoU mede sobreposição de caixas envolventes; não garante enquadramento perfeito de toda a borda nem legibilidade dos caracteres. As caixas de referência são marcações manuais, não anotações oficiais do conjunto de origem.

## Independência da versão Java

A solução Python não importa, chama ou exige nenhum arquivo Java. A arquitetura é funcional, usa vetorização NumPy e JSON, e tem propostas por black-hat/Sobel, medidas de distribuição de traços e quadriláteros estimados dos contornos. Compartilha com a versão Java o objetivo, técnicas clássicas gerais, fotografias e algumas referências usadas para comparar os resultados. A partir da versão 1.1.0, compartilha também a ideia do refinamento de bordas pela estrutura da placa: o método foi desenvolvido e validado primeiro na versão Java e depois reescrito aqui com NumPy, sem reutilizar código Java. A regra de faixa acima do corpo existe só na versão Python. Não se espera igualdade de coordenadas entre algoritmos distintos.

## Limitações

- A amostra é pequena e os positivos vêm de uma única coleção; não há garantia de precisão geral ou acerto em todas as placas egípcias.
- O método não verifica semanticamente a presença de um veículo. Texturas, fachadas e letreiros podem causar falsos positivos.
- Uma única placa é escolhida por fotografia, mesmo que existam vários veículos.
- Perspectiva extrema, oclusão, borrão, placas minúsculas e noite muito escura podem falhar. Os testes com escurecimento e perspectiva são derivações controladas de uma foto, não uma coleção independente dessas situações.
- Alguns recortes ainda cortam o topo da faixa (`img_016`, `img_021`, `img_026`), e em outros o refinamento inclui um pouco de fundo acima dela (`img_048`, `img_049`). `margem` permite aumentar o espaço ao redor, com possível inclusão de fundo.
- A orientação EXIF é ignorada intencionalmente para manter coordenadas referidas aos pixels armazenados. Fotos que dependem de EXIF para ficarem em pé devem ser rotacionadas antes.
- Salvar a original e todas as intermediárias aumenta tempo e espaço em disco; desative essa opção em lotes grandes.
- Limites de tamanho e contornos reduzem consumo de recursos, mas não são uma cota rígida de memória nem garantia de tempo máximo.

## Fontes

As fotografias, hashes e licenças são descritos em [FONTES-IMAGENS.md](docs/FONTES-IMAGENS.md). Os arquivos originais das miniaturas apresentadas no enunciado não foram fornecidos; esta entrega usa fotografias públicas identificadas e incluídas no projeto.

Dependências: `opencv-python-headless`, NumPy e Pillow. A distribuição headless fornece `cv2` sem dependências de janelas gráficas. Os testes utilizam `unittest`, da biblioteca padrão.
