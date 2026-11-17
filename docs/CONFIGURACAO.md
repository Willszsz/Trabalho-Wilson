# Parâmetros

Use `python main.py --config arquivo.json`. O arquivo pode conter apenas as chaves alteradas. Valores decimais usam ponto.

| Parâmetro | Padrão | Intervalo | Significado |
|---|---:|---|---|
| `lado_maximo` | 1400 | 320 a 3000 | Maior lado da cópia de trabalho, em pixels. |
| `max_megapixels` | 40 | 1 a 60 | Limite de entrada em milhões de pixels. |
| `max_arquivo_mb` | 50 | 1 a 200 | Limite de entrada em MiB (1024² bytes). |
| `gaussiano` | 3 | 1 a 15 | Lado ímpar do kernel Gaussiano. |
| `contraste_local` | 2.0 | 0.1 a 8 | Limite de contraste do CLAHE; grade interna 8 × 8. |
| `canny_baixo` | 45 | 1 a 254 | Limiar inferior de Canny na imagem realçada. |
| `canny_alto` | 135 | 2 a 255 | Limiar superior de Canny; maior que o inferior. |
| `fechamento_x` | 0.012 | 0.001 a 0.08 | Largura do kernel como fração da largura de trabalho; mínimo 3 e ímpar. |
| `fechamento_y` | 0.003 | 0.001 a 0.04 | Altura do kernel como fração da altura de trabalho; mínimo 3 e ímpar. |
| `razao_min` | 1.3 | 1 a 6 | Menor proporção largura/altura aceita. |
| `razao_max` | 5.5 | 1.1 a 10 | Maior proporção largura/altura aceita. |
| `area_min` | 0.00045 | 1e-05 a 0.1 | Menor área de candidato dividida pela área da imagem de trabalho. |
| `area_max` | 0.22 | 0.001 a 0.8 | Maior fração de área aceita. |
| `largura_min` | 32 | 12 a 400 | Largura mínima do candidato na imagem de trabalho. |
| `altura_min` | 12 | 6 a 200 | Altura mínima do candidato na imagem de trabalho. |
| `inclinacao_max` | 35 | 0 a 70 | Inclinação absoluta máxima em graus. |
| `saturacao_min` | 85 | 0 a 255 | Mínimo do canal S de HSV (0 a 255) para faixas coloridas. |
| `brilho_cor_min` | 45 | 0 a 255 | Mínimo do canal V de HSV (0 a 255) para faixas coloridas. |
| `contraste_min` | 20 | 1 a 150 | Diferença mínima entre percentis 90 e 10 da intensidade do recorte. |
| `bordas_min` | 0.035 | 0.001 a 0.4 | Densidade mínima de bordas no candidato normalizado. |
| `bordas_max` | 0.48 | 0.1 a 0.95 | Densidade máxima de bordas no candidato normalizado. |
| `marcas_min` | 3 | 1 a 15 | Mínimo de componentes escuros compatíveis com traços; não reconhece caracteres. |
| `ocupacao_min` | 0.38 | 0.1 a 0.9 | Distância entre os centros das marcas extremas dividida pela largura normalizada. |
| `nota_min` | 0.8 | 0 a 1 | Limiar da pontuação heurística para aceitar a melhor região. |
| `razao_preferida` | 2.3 | 1 a 6 | Proporção largura/altura que recebe a nota máxima no critério de formato. Deve ficar entre `razao_min` e `razao_max`. Até a versão 1.0.0 era uma constante no código. |
| `margem` | 0.035 | 0 a 0.15 | Margem de recorte adicionada por lado como fração da dimensão. |
| `refinar_bordas` | 1 | 0 a 1 | 1 ativa o refinamento de bordas da região escolhida; 0 reproduz o comportamento da versão 1.0.0. |
| `expansao_largura` | 0.2 | 0 a 0.5 | Quanto a janela de refinamento se estende para cada lado, como fração da largura da região. Limita o quanto a borda pode crescer. |
| `expansao_altura` | 0.35 | 0 a 0.8 | O mesmo, para cima e para baixo, como fração da altura. |
| `limite_contornos` | 8000 | 100 a 30000 | Máximo de contornos por máscara, priorizando os maiores. |

Os parâmetros cujo padrão é inteiro exigem números inteiros no JSON. `true`/`false` não são aceitos como números. Mínimos devem ser menores que máximos; `gaussiano` deve ser ímpar. Valores não finitos e propriedades desconhecidas são rejeitados. A configuração efetiva é gravada no resultado de cada imagem.

A pontuação usa pesos fixos de projeto: proporção 0,15; marcas 0,23; ocupação 0,18; contraste 0,10; densidade 0,10; distribuição 0,09; faixa colorida 0,10; fundo 0,05. As medidas são normalizadas antes da soma. As constantes de normalização e as hipóteses de proporção estão em `processamento/detector.py` e podem ser modificadas para estudo. Não são pesos aprendidos por treinamento.

O limiar inicial 0,58 aceitou dois falsos positivos de textura. O padrão final 0,80 foi ajustado usando as imagens conhecidas e os quatro negativos; a avaliação nas dez imagens reservadas ocorreu depois desse ajuste. Esse limiar não significa 80% de confiança.

## Constantes internas do refinamento

`processamento/refinamento.py` usa limiares fixos de projeto: croma mínimo 0,35 para estimar o matiz da faixa, croma abaixo de 0,30 para pixel neutro claro, tolerância de matiz de 22°, fração mínima de 0,20 por coluna e 0,25 por linha. A região refinada é descartada se a largura ficar fora de 0,55 a 1,4 vezes a original, a altura fora de 0,6 a 1,6 vezes, a proporção fora de `razao_min` a `razao_max`, menos de 60% dela estiver dentro da região original, ou o contraste ficar abaixo de `contraste_min`.

A regra de faixa acima usa uma janela própria, 1,3 larguras para cada lado e 0,9 altura para cima e para baixo. Ela só é aplicada quando a região escolhida não tem faixa colorida no topo. Nesse caso, aceita até 2,6 vezes a largura e a altura originais, desde que a faixa encontrada tenha o matiz dominante logo acima da região e termine dentro da janela.
