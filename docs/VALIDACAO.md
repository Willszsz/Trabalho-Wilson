# Validação da implementação Python

## Versão 1.1.0

Executada em 17/11/2026 em Linux x64, com OpenCV 4.13.0, NumPy 2.3.5 e Pillow 12.0.0. **Os 32 testes passaram em Python 3.11.18, 3.12.16, 3.13.18 e 3.14.10.** [Log dos testes](testes.log). Windows não foi executado neste ambiente.

### O que mudou e por quê

1. **Dependências.** A versão 1.0.0 fixava `numpy==2.2.6` e `opencv-python-headless==4.12.0.88`. O NumPy 2.2.6 não tem pacote para Python 3.14, e o OpenCV 4.12 exige `numpy<2.3`, que também não tem. Resultado verificado: em Python 3.14, `pip install -r requirements.txt` falhava com `No matching distribution found for numpy==2.2.6`. A versão 1.1.0 fixa OpenCV 4.13.0.92 e NumPy 2.3.5, que têm pacotes de Python 3.11 a 3.14. Antes de qualquer outra mudança, o código 1.0.0 foi reavaliado com as dependências novas: **as caixas e os IoUs das 35 fotografias com referência e o lote das 50 fotografias ficaram idênticos.** Python 3.10 deixa de ser suportado, porque o NumPy 2.3 exige 3.11 ou superior.
2. **Refinamento de bordas** (`processamento/refinamento.py`). Na 1.0.0, a faixa superior saía cortada em vários recortes (`img_039`, `img_040`, `img_048`, `img_049`, entre outros). Depois da seleção, uma janela ampliada em torno da região é retificada a partir da imagem original e cada pixel é classificado como corpo claro neutro ou cor da faixa, com o matiz dominante estimado na própria região. Uma coluna só pertence à placa se tiver cor da faixa em cima e corpo claro embaixo; o topo é procurado no perfil da faixa e a base no perfil do corpo. Se não houver fronteira clara ou a nova região violar proporção, tamanho ou contraste, a região original é mantida. O método foi desenvolvido e validado primeiro na versão Java do mesmo trabalho e depois reescrito aqui com NumPy.
3. **Faixa acima do corpo.** Em `img_031`, a 1.0.0 marcou como placa apenas a metade dos números, sem faixa e sem letras, e informou sucesso. Quando a região escolhida não tem faixa no topo, o refinamento procura, logo acima dela, uma faixa com o matiz dominante daquele trecho. Se encontrar, a placa passa a ir do topo da faixa até a base do corpo, na largura da faixa. A primeira versão dessa regra considerava qualquer pixel saturado e tomou a lataria vermelha do carro como faixa; por isso a regra exige o matiz dominante e que a faixa termine dentro da janela de busca. Nas 50 fotografias, a regra só foi acionada em `img_031`.
4. **`razao_preferida` configurável**, em vez da constante 2,3 no código. O valor padrão não mudou.

### Protocolo

`img_031` a `img_050` foram copiadas do mesmo commit da fonte. As caixas de `img_036` a `img_050` foram marcadas manualmente para a avaliação da versão Java, antes de qualquer alteração nela. **Ressalva:** os recortes da versão Python 1.0.0 nessas 15 fotografias foram observados antes desta correção, e a faixa cortada de `img_039`, `img_040`, `img_048` e `img_049` motivou parte do trabalho. Elas não são, portanto, uma avaliação completamente cega da 1.1.0. O método de refinamento em si foi ajustado em fotografias de desenvolvimento da versão Java, não nessas.

### Resultados

| Conjunto | 1.0.0 | 1.1.0 |
|---|---|---|
| `img_021` a `img_030` (reservadas da 1.0.0) | 10/10, IoU médio 0,797, pior 0,679 | 10/10, IoU médio 0,837, pior 0,757 |
| `img_011` a `img_020` (comparação) | 10/10, IoU médio 0,800, pior 0,642 | 10/10, IoU médio 0,808, pior 0,677 |
| `img_036` a `img_050` (novas) | 15/15, IoU médio 0,847, pior 0,771 | 15/15, IoU médio 0,845, pior 0,737 |
| Lote de 50 fotografias | 50 regiões; `img_031` só com os números | 50 regiões; `img_031` com a placa inteira |
| 4 fotografias sem veículo | 0 detecções | 0 detecções |

Nas novas, o IoU médio ficou estável. Visualmente, a faixa superior passou a aparecer completa em `img_039`, `img_040`, `img_048` e `img_049`; em `img_048` e `img_049` o recorte também ganhou fundo acima da faixa, o que reduziu o IoU desses dois casos. `img_016`, `img_021` e `img_026` ainda cortam o topo da faixa, como na 1.0.0.

[CSV 021 a 030](avaliacao-python.csv) · [CSV 011 a 020](comparacao-python.csv) · [CSV 036 a 050](avaliacao-novas.csv) · [Referências 036 a 050](referencias-novas.csv) · [Comparação 1.0.0 e 1.1.0 em 031 a 050](novas-comparacao.jpg) · [Recortes 021 a 030](reservadas.jpg) · [Log](avaliacao-novas.log)

Os CSVs da 1.0.0 foram preservados com o sufixo `-v1.0.0`. Todas as 50 fotografias vêm de uma única coleção, com condições parecidas; os números não permitem afirmar uma taxa de acerto geral.

---

## Versão 1.0.0


Executada em 17/11/2026 com Python 3.12.14, OpenCV 4.12.0, NumPy 2.2.6 e Pillow 12.0.0, em Linux x64. O programa não depende de Java. A execução em Windows não foi verificada neste ambiente.

### Testes automatizados e terminal

**30 testes unittest passaram**, com subcasos que incluem múltiplos formatos, valores de configuração e transformações de imagem. A quantidade de testes não equivale ao número de fotografias distintas. [Log completo](testes.log).

Foram verificados: cinza com valores conhecidos; preservação da matriz de entrada; fatias NumPy não contínuas; leitura JPG/JPEG/PNG; espaços e acentos; arquivo inexistente; formato inválido; corrupção e truncamento; PNG com checksum inválido; limite de pixels e bytes; prevenção de sobrescrita; configuração inválida; geometria; retificação; intermediárias ligadas/desligadas; erro de gravação; lote com erro individual e continuação; diretórios recursivos; histórico; argumentos e códigos de saída; ausência de veículo; preservação da fotografia original.

O teste do menu executou todas as opções 1 a 6 e saída 0 usando entradas de terminal automatizadas. O detector e a gravação executaram de fato; não foram substituídos por resultados simulados. O teste percorreu histórico vazio, exemplo real, imagem personalizada real, lote, consulta de etapas salvas/não salvas, informações e opção inválida.

### Calibração e investigação de falhas

`img_001` a `img_020` são fotografias conhecidas da etapa anterior em Java. Foram usadas para desenvolvimento e comparação, não como teste independente da versão Python. Seus vinte recortes foram inspecionados visualmente e correspondem às placas. [Montagem da rodada inicial](calibracao.jpg).

A primeira configuração, com `nota_min = 0.58`, aceitou duas regiões de grama: uma em `camera.png`, com nota 0,675, e outra em `grass.png`, com nota 0,744. A textura produzia bordas e componentes parecidos com traços, mas não havia placa. A análise motivou um limiar padrão de **0,80**. As placas conhecidas pontuaram acima de 0,88, preservando sua seleção.

Com o limiar final, os quatro negativos (`camera`, `coffee`, `astronaut`, `grass`) produziram **0 detecções em 4 fotografias**, também verificadas nos testes. Esses negativos participaram da calibração: o resultado não é uma estimativa independente da taxa de falsos positivos. [Log do lote negativo final](negativas.log).

### Dez fotografias reservadas

`img_021` a `img_030` foram obtidas da mesma fonte pública e separadas da coleção de desenvolvimento. As referências foram marcadas manualmente nas fotografias e conferidas por recortes, antes de executar o detector nessas imagens. A geometria das caixas pode conter pequenas imprecisões de anotação visual; não se trata de uma segmentação pixel a pixel.

A versão com limiar 0,80 foi avaliada sem reajustar o detector após observar esses resultados. **10/10 fotografias atingiram IoU ≥ 0,50**, sem falhas de execução. Os recortes também foram inspecionados visualmente. Isso não permite afirmar 100% de precisão geral: são somente dez imagens de uma coleção e não uma amostra representativa de todas as condições de tráfego egípcias.

| Arquivo | IoU | Critério ≥ 0,50 |
|---|---:|---|
| img_021.jpg | 0.856 | Atendido |
| img_022.jpg | 0.769 | Atendido |
| img_023.jpg | 0.757 | Atendido |
| img_024.jpg | 0.812 | Atendido |
| img_025.jpg | 0.785 | Atendido |
| img_026.jpg | 0.774 | Atendido |
| img_027.jpg | 0.822 | Atendido |
| img_028.jpg | 0.893 | Atendido |
| img_029.jpg | 0.824 | Atendido |
| img_030.jpg | 0.679 | Atendido |

[CSV calculado](avaliacao-python.csv) · [Referências manuais](referencias-python.csv) · [Montagem visual](reservadas.jpg) · [Recortes individuais](recortes/) · [Log](avaliacao.log)

IoU é a área de interseção dividida pela área da união das caixas envolventes na imagem original. Não mede OCR, qualidade dos caracteres nem o enquadramento perfeito de cada canto. Algumas extrações ficam próximas da borda superior; ainda é possível melhorar a estimativa das margens.

### Comparação descritiva com Java

A tabela usa as mesmas fotografias `img_011` a `img_020` e as mesmas referências da entrega Java. O método Python seleciona candidatos por regras próprias, inclusive agrupamentos de textura e hipóteses expandidas. Os resultados não foram forçados a coincidir.

| Imagem | IoU Java | IoU Python |
|---|---:|---:|
| img_011.jpg | 0.734 | 0.803 |
| img_012.jpg | 0.839 | 0.851 |
| img_013.jpg | 0.420 | 0.909 |
| img_014.jpg | 0.000 | 0.710 |
| img_015.jpg | 0.868 | 0.874 |
| img_016.jpg | 0.758 | 0.642 |
| img_017.jpg | 0.808 | 0.738 |
| img_018.jpg | 0.855 | 0.843 |
| img_019.jpg | 0.820 | 0.837 |
| img_020.jpg | 0.784 | 0.790 |

Nessas dez imagens, Java atendeu ao critério em 8/10 e Python em 10/10. Python recuperou a região desgastada de `img_014` por textura e reduziu o excesso de fundo de `img_013` com uma proposta expandida de bordas. **Essa comparação não prova superioridade geral**: as dez fotos já eram conhecidas durante o desenvolvimento Python e as implementações usaram procedimentos diferentes de ajuste. As novas imagens 21–30 são a avaliação separada desta versão.

[CSV Java preservado](avaliacao-java.csv) · [CSV Python](comparacao-python.csv) · [Referências compartilhadas](referencias-comparacao.csv)

### Luz, resolução, rotação e perspectiva

A fotografia real `img_003` foi testada na forma original e com seis derivações: intensidade multiplicada por 0,32; redução a 600 × 800; ampliação a 2400 × 3200; rotação de 12°; pequena deformação de perspectiva; remoção de cor. Os sete subcasos passaram com IoU ≥ 0,50. As referências são transformadas matematicamente junto com a imagem; a detecção continua automática.

Esses subcasos testam o comportamento sob transformações controladas. Não são sete fotografias independentes e não substituem um conjunto de capturas reais noturnas ou em perspectiva extrema.

### Reproduzir

```text
pip install -r requirements.txt
python -m unittest discover -v
python avaliar.py --pasta imagens/reservadas --referencias docs/referencias-python.csv --saida resultados/avaliacao
python avaliar.py --pasta imagens/carros --referencias docs/referencias-comparacao.csv --saida resultados/comparacao
```

O avaliador grava novos relatórios, imagens anotadas e recortes em pastas exclusivas. Retorna 0 se todas as caixas atingirem o critério, 1 se alguma não atingir e 2 se houver erro de execução. Os logs arquivados contêm os caminhos do ambiente onde foram gerados. As execuções locais usam os caminhos da máquina do usuário.
