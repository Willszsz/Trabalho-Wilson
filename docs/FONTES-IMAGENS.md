# Fontes das fotografias

As 50 imagens de veículos foram preservadas sem alteração, provenientes do [conjunto de Ahm3d0x](https://github.com/Ahm3d0x/Automatic-License-Plate-Recognition-Classical-Image-Processing-/tree/612bcd8b09aace4181b8737dc0e739823902db03/dataset), commit `612bcd8b09aace4181b8737dc0e739823902db03`.

- `imagens/carros/img_001.jpg` a `img_020.jpg`: imagens conhecidas para demonstração, desenvolvimento e comparação com a versão Java.
- `imagens/reservadas/img_021.jpg` a `img_030.jpg`: avaliação separada da implementação Python 1.0.0.
- `imagens/novas/img_031.jpg` a `img_050.jpg`: incluídas na versão 1.1.0, do mesmo commit. `img_031` a `img_035` serviram de desenvolvimento; `img_036` a `img_050` têm caixas de referência em `referencias-novas.csv`, marcadas manualmente antes das alterações da versão Java 1.1.0.

A licença MIT publicada pelo repositório de origem está preservada em `LICENCA-DATASET.txt`. Apenas as fotografias foram usadas; nenhum código de OCR ou modelo desse projeto é executado.

As quatro fotografias sem veículo vieram do [scikit-image v0.19.3](https://github.com/scikit-image/scikit-image/tree/v0.19.3/skimage/data). Atribuições conforme a [documentação das amostras](https://github.com/scikit-image/scikit-image/blob/v0.19.3/skimage/data/_fetchers.py):

| Arquivo | Fonte | Condição informada |
|---|---|---|
| camera.png | Lav Varshney | CC0 |
| coffee.png | Rachel Michetti; cortesia Pikolo Espresso Bar | CC0 |
| astronaut.png | NASA, fotografia de Eileen Collins | Domínio público |
| grass.png | linolafett, Grass-01 | CC0 |

A licença do scikit-image está em `LICENCA-SKIMAGE.txt`. Os hashes de todas as fotografias estão em `imagens-sha256.txt`. As referências em CSV foram marcadas manualmente para as avaliações e não vieram como anotações oficiais da fonte.

A apresentação com miniaturas fornecida no pedido original não contém as fotografias originais em resolução apropriada. Esta entrega usa o conjunto público acima, identificado para permitir reprodução dos testes.
