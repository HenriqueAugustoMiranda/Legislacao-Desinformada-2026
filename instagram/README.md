## 1. Coleta de Dados do Instagram

### 1.1. Configurações e Execução

Os perfis-alvo da coleta são os perfis do Instagram cujos posts e comentários serão baixados e analisados. Eles são configurados manualmente em [data/utils.py](data/utils.py) na função `get_users` — qualquer @ de perfil adicionado à lista será incluído nas próximas execuções dos scripts de coleta.

Para que a coleta funcione, é necessário fornecer um **`sessionid`** válido do Instagram — um token de autenticação gerado quando um usuário faz login no Instagram pelo navegador. Ele identifica a sessão de uma conta real e é o que permite que os scripts acessem a API privada do Instagram em nome dessa conta. O `sessionid` é configurado em [data/utils.py](data/utils.py) na função `get_sessionid` e deve ser atualizado manualmente sempre que a sessão expirar.

**Como obter o `sessionid`:**
1. Acesse o Instagram pelo navegador e faça login normalmente
2. Abra o DevTools (F12 ou clique direito → Inspecionar)
3. Vá na aba **Application** (Chrome/Edge) ou **Storage** (Firefox)
4. No menu lateral, expanda **Cookies** → `https://www.instagram.com`
5. Localize o cookie chamado **`sessionid`** e copie o valor da coluna **Value**
6. Cole o valor na função `get_sessionid()` em [data/utils.py](data/utils.py)

A coleta **não é automática nem contínua**: ela ocorre sob demanda, executando os scripts na ordem abaixo a partir da pasta `data/`:

```bash
cd data
python 01_collect_posts.py      # coleta de posts
python 02_collect_comments.py   # coleta de comentários dos posts
```

O script de comentários depende dos arquivos `data/out_instagram/{username}/posts.json` gerados pelo primeiro script, por isso a ordem de execução importa. Ambos imprimem o progresso no terminal.

Caso a coleta começe a falhar com erros de autenticação, basta repetir o processo e atualizar o valor.

---

### 1.2. Processo de Coleta

A coleta é feita em duas etapas sequenciais, usando a biblioteca `instagrapi` ([`GitHub`](https://github.com/subzeroid/instagrapi)), que acessa a API privada do Instagram autenticando com um `sessionid` de sessão. As credenciais e a lista de perfis-alvo são centralizadas em [data/utils.py](data/utils.py).

#### Coleta de Posts ([data/01_collect_posts.py](data/01_collect_posts.py))

O script faz login via `sessionid` e, para cada perfil da lista, busca os posts com paginação usando o endpoint privado `feed/user/{user_id}/`, em lotes de 30 posts por vez (`BATCH_POSTS = 30`).

A coleta respeita uma **data limite configurável**: apenas posts publicados a partir de uma data mínima são coletados. Ela é definida diretamente em:

```python
DATA_LIMITE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TZ_BR).timestamp()  # ano, mês, dia
USAR_DATA_LIMITE = True  # False coleta sem limite de data
```

O horário da coleta é obtido do servidor do Instagram (via header `Date` HTTP). Intervalos aleatórios de espera entre páginas (`1.5–3.0s`) e entre perfis (`3.0–6.0s`) são usados para evitar bloqueio.

**Dados Coletados (`data/out_instagram/{username}/posts.json`**):

| Campo | Descrição |
|---|---|
| `username` | Nome do perfil |
| `media_pk` | ID único do post no Instagram |
| `shortcode` | Código curto (usado na URL do post) |
| `url` | Link direto para o post |
| `taken_at` | Timestamp de publicação |
| `taken_at_br` | Data/hora formatada no fuso de Brasília |
| `media_type` / `media_type_label` | Tipo da mídia: `photo`, `video` ou `album` |
| `caption` | Texto/legenda do post |
| `like_count` | Número de curtidas |
| `comment_count` | Número de comentários |
| `collected_at` / `collected_at_br` | Timestamp da coleta |

#### Coleta de Comentários ([data/02_collect_comments.py](data/02_collect_comments.py))

Depende do arquivo `posts.json` gerado na etapa anterior. Para cada post, busca **todos os comentários principais** via endpoint `media/{media_pk}/comments/` com paginação bidirecional (`max_id` e `min_id`), e também **todas as respostas (replies)** de cada comentário via `media/{media_pk}/comments/{comment_pk}/child_comments/`.

O script é **retomável**: se o arquivo JSON de um post já existe, ele é pulado. Erros HTTP 403 consecutivos interrompem a coleta do perfil para evitar agravamento de bloqueios.

Estrutura de pastas dos comentários:
```
data/out_instagram/<username>/comments/<ano>/<mes-dia>/<hora>_<shortcode>.json
```

**Dados Coletados**:

| Campo | Descrição |
|---|---|
| `username` | Nome do perfil |
| `media_pk` / `shortcode` / `url` / `taken_at_br` | Identificadores do post pai |
| `collected_at` / `collected_at_br` | Timestamp da coleta (servidor) |
| `n_parent_comments` | Número de comentários principais coletados |
| `n_total_replies` | Total de respostas coletadas |
| `check.expected_comment_count_from_post` | Contagem esperada segundo o post |
| `check.got_total` / `check.diff` | Contagem real e diferença |
| `comments[].comment_id` | ID único do comentário |
| `comments[].created_at` / `created_at_br` | Data/hora do comentário |
| `comments[].comment_user` | Usuário que comentou |
| `comments[].text` | Texto do comentário |
| `comments[].like_count` | Curtidas no comentário |
| `comments[].reply_count` | Número de respostas |
| `comments[].replies[]` | Lista de respostas (mesma estrutura do comentário pai) |