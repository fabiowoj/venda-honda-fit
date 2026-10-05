# Honda New Fit 2009 — site de venda

Site de uma página para vender o Honda Fit LX 1.4 2009: vídeo que gira com o scroll, comparação automática com a tabela FIPE, galeria e contato por WhatsApp/e-mail.

**No ar:** https://fabiowoj.github.io/venda-honda-fit/

HTML, CSS e JavaScript puros, sem dependências nem etapa de build. Publicado pelo GitHub Pages direto da branch `main`.

```
index.html            a página (textos, preço, links)
fotos.json            lista de fotos: nome, descrição, giro e área a esconder (placa)
fotos-originais/      suas fotos originais — NÃO vai para o git (tem GPS e placa)
assets/img/           fotos prontas para a web (geradas pelo script)
assets/video/         vídeo da abertura, versões 1280 e 720 px (gerados pelo script)
assets/css, js, fonts estilo, animações e a fonte Archivo (hospedada aqui mesmo)
scripts/fotos.py      prepara fotos e vídeo e atualiza galeria, JSON-LD e sitemap
scripts/verificar.py  checagem de segurança/SEO (roda sozinha a cada push)
robots.txt, sitemap.xml, llms.txt, site.webmanifest, 404.html
```

## Trocar ou adicionar fotos

Uma vez só: `pip install pillow imageio-ffmpeg`

1. Coloque a foto em `fotos-originais/` com um nome simples, sem espaços nem acentos. Exemplo: `fotos-originais/roda.jpg`.
2. No `fotos.json`:
   - **para trocar** uma foto, use o mesmo nome (`id`) de uma que já existe;
   - **para adicionar**, copie um bloco e mude o `id` para o nome do arquivo sem a extensão (`"id": "roda"`), o `alt` (descrição para o Google e para leitores de tela) e a `legenda`.
   - `"girar": 90` se a foto ficar deitada (90, 180 ou 270, sentido horário).
   - `"galeria": false` se não quiser a foto na galeria.
3. Rode:
   ```
   python3 scripts/fotos.py --conferir
   ```
   Isso gera as versões para a web **sem metadados** (remove o GPS do celular), atualiza a galeria, os dados para o Google e o `sitemap.xml`. Com `--conferir`, ele também salva em `fotos-originais/_conferir/` uma prévia com a área escondida marcada em vermelho.
4. Publique: `git add -A && git commit -m "Troca fotos" && git push`. Em 1 ou 2 minutos o site atualiza.

A ordem da galeria é a ordem do `fotos.json`.

### Esconder a placa em uma foto nova

A placa é **apagada dentro do próprio arquivo**, e não só coberta na página, então ninguém consegue ver abrindo a imagem direto.

Em `ocultar`, cada área é `[x, y, largura, altura]` em **porcentagem** da foto já endireitada, medida a partir do canto superior esquerdo. Exemplo: `"ocultar": [[37.8, 72.2, 21.4, 5.9]]` = começa a 37,8% da esquerda e a 72,2% do topo, com 21,4% de largura e 5,9% de altura.

Para descobrir os números, abra a foto num editor como o Paint ou o Fotos, veja a posição em pixels do canto da placa e divida pela largura (ou altura) total da foto. Rode com `--conferir` e confira a prévia. Se precisar, dá para colocar várias áreas: `[[...], [...]]`.

### Trocar o vídeo

Salve como `fotos-originais/video-original.mp4` e rode `python3 scripts/fotos.py`. O script gera as duas versões (com um quadro-chave a cada 4 quadros, para acompanhar o scroll sem engasgar), o pôster e a imagem de compartilhamento `assets/og-image.jpg`. Ele não apaga placas no vídeo: o vídeo atual já não mostra a placa.

## Marcar como vendido

**Pelo GitHub (até pelo celular):**
1. Abra a aba **Actions** do repositório → **Vendido / à venda** (na lista da esquerda).
2. Toque em **Run workflow**, escolha **vendido** (ou **à venda** para desfazer) e confirme.
3. Em 1 ou 2 minutos o site atualiza.

**Pelo computador:** `python3 scripts/vendido.py sim` (ou `nao`), depois commit e push.

Quando vendido, o site mostra o carimbo **VENDIDO**, o preço riscado e um agradecimento no lugar do contato. Somem os botões de WhatsApp e e-mail e os links da OLX e da Webmotors. O título e os dados para o Google passam a dizer "vendido", e a página pede para sair da busca (`noindex`), para ninguém mais ligar procurando o carro. Tudo volta com **à venda**.

Os textos das duas versões ficam no `index.html`, marcados com `data-se="a-venda"` ou `data-se="vendido"`.

## Mudar preço, textos e links

Tudo fica no `index.html`:

- **Preço:** procure `37.500` e `37500`. O valor aparece no título, na descrição, nos metadados, no JSON-LD (`"price"`), no `data-preco` e nos textos. Troque também no `llms.txt`.
- **FIPE:** atributos `data-fipe-*` da seção `#preco`. O site busca o valor atualizado na BrasilAPI sempre que abre e guarda o resultado por 12 horas. Se a busca falhar, usa `data-fipe-valor` (R$ 39.514, setembro de 2026). O código 014039-2 é o da versão manual.
- **Anúncios da Webmotors e da OLX:** no fim do `index.html`, cole a URL no `href=""` de cada anúncio e apague a palavra `hidden`. Enquanto estiverem vazios, os botões ficam escondidos.

## Segurança e privacidade

- **Fotos sem metadados:** as fotos do celular tinham as **coordenadas GPS** de onde foram tiradas. O script remove esses dados, e o `verificar.py` bloqueia o push se alguma foto publicada ainda tiver EXIF.
- **Placa apagada nos arquivos:** a versão anterior só cobria a placa com um quadrado na página, e o quadrado nem estava no lugar certo em algumas fotos. Agora a placa é borrada na própria imagem.
- **Originais fora do git:** `fotos-originais/` está no `.gitignore`, e a verificação falha se algum arquivo dela for versionado.
- **Content Security Policy:** só carrega scripts, estilos, fontes e mídia do próprio site, e só se conecta à BrasilAPI. Não tem script inline, `style=""` inline nem serviço de terceiros; a fonte é hospedada aqui.
- A resposta da FIPE é validada (número entre R$ 5 mil e R$ 300 mil) e inserida só como texto, nunca como HTML.
- Links externos usam `rel="noopener noreferrer"`. Sem cookies, sem analytics, sem formulários.
- O GitHub Pages serve tudo por HTTPS. Como ele não permite cabeçalhos HTTP próprios, a política de segurança vai em `<meta>`. Isso significa que `frame-ancestors` (bloquear o site dentro de iframes de terceiros) não tem efeito. Para ter isso, use Cloudflare na frente ou um host como Netlify ou Vercel.
- Telefone e e-mail aparecem na página de propósito, para contato. Robôs de spam podem coletá-los; o filtro do Gmail costuma dar conta.

## SEO (Google e assistentes de IA)

- `<title>`, descrição, `canonical`, Open Graph (prévia bonita no WhatsApp e nas redes) e Twitter Card, com `assets/og-image.jpg` em 1200×630.
- **Dados estruturados** (JSON-LD `Car` + `Offer`): preço, km, ano, câmbio, cor, interior, número de donos e fotos.
- `sitemap.xml` com as imagens, `robots.txt` liberando Google, Bing e os robôs de IA (GPTBot, ClaudeBot, PerplexityBot e outros), e `llms.txt` com a ficha do carro em texto simples para os assistentes de IA.
- HTML semântico: um único `h1`, `alt` descritivo em todas as fotos e o conteúdo todo no HTML, não montado por JavaScript.
- Desempenho: fotos em WebP com duas resoluções, lazy loading, fonte pré-carregada, vídeo menor para celular e dimensões fixas nas imagens, para a página não "pular" enquanto carrega.

### Depois de publicar

1. **Google Search Console** (https://search.google.com/search-console): adicione a propriedade com o prefixo de URL `https://fabiowoj.github.io/venda-honda-fit/`, verifique pelo método de arquivo HTML (coloque o arquivo que o Google fornecer na raiz deste repositório) e envie o `sitemap.xml`. Depois use "Inspeção de URL → Solicitar indexação".
2. **Bing Webmaster Tools**: importe do Search Console. O Bing também alimenta o ChatGPT e o Copilot.
3. Teste os dados estruturados em https://search.google.com/test/rich-results e a prévia de compartilhamento colando o link no WhatsApp.
4. Coloque o link do site nos anúncios da OLX e da Webmotors, e os links deles aqui. Links entre as páginas ajudam o Google a encontrar o site.

**Observação:** num site de projeto do GitHub Pages (`usuario.github.io/projeto/`), os robôs procuram `robots.txt` e `llms.txt` na raiz do domínio (`fabiowoj.github.io/robots.txt`), e não nesta pasta. Sem esse arquivo, tudo é liberado por padrão, então não há problema. O sitemap funciona normalmente quando enviado pelo Search Console. Com um domínio próprio, os dois arquivos passam a valer como estão.

## Verificar antes de publicar

```
python3 scripts/verificar.py
```

O mesmo teste roda no GitHub Actions a cada push (aba **Actions**).

## Créditos

Fonte [Archivo](https://fonts.google.com/specimen/Archivo), da Omnibus-Type, licença SIL Open Font License 1.1. Anúncio pessoal, sem vínculo com a Honda.
