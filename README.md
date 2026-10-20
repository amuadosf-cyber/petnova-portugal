# PetNova Portugal

Loja portuguesa de acessórios para cães e gatos, **em demonstração**. Não existem encomendas, cobranças ou fornecedores confirmados.

- [Abrir a loja](https://amuadosf-cyber.github.io/petnova-portugal/)
- [Ver o estúdio e o vídeo de exemplo](https://amuadosf-cyber.github.io/petnova-portugal/studio.html)
- [Descarregar os conteúdos diários no GitHub Actions](https://github.com/amuadosf-cyber/petnova-portugal/actions/workflows/conteudos.yml)

## O que esta versão faz

| Função | Estado |
| --- | --- |
| Catálogo, filtros e carrinho | Demonstração; compra permanentemente desativada nesta versão |
| Anúncios | PNG 1080 × 1350 com aviso de demonstração |
| Vídeos | MP4 1080 × 1920, H.264, 24 segundos, quatro cenas animadas, pista AAC silenciosa |
| Legendas e guiões | TikTok, Instagram e YouTube; SRT e calendário diário |
| Preparação diária | GitHub Actions, dois rascunhos por dia, sem depender do PC |
| IA | Qwen3 via Ollama no runner gratuito para assistir os títulos; Ollama no PC é opcional; fallback identificado para modelos de texto |
| YouTube e Instagram | Adaptadores oficiais implementados e testados com respostas simuladas; contas por ligar |
| TikTok | Exportação dos ficheiros para publicação/agendamento nativo; sem envio automático |
| Publicações reais | Desativadas; nenhum acesso às contas é incluído no site |

Os vídeos atuais são **vídeos gráficos com ilustrações originais**, não filmagens geradas por IA. O exemplo público foi criado sem Ollama. A integração de IA tem testes com respostas simuladas e falhas de ligação. Consulta o manifesto de cada execução para saber se foi usada IA real (`ai_used: true`) ou um modelo de texto (`ai_used: false`). Não existe serviço gratuito de geração de filmagens integrado nesta versão.

A criação de anúncios não compra publicidade nem inicia campanhas pagas.

## Automação no GitHub, sem PC

O workflow tenta preparar Ollama e o modelo gratuito **Qwen3 0.6B** no próprio runner, usando CPU e sem enviar dados a uma API paga. Se a preparação falhar ou a resposta for rejeitada, continua com modelos de texto; o manifesto identifica o gerador usado. O modelo é descarregado no runner temporário, não no teu PC. Na execução manual podes desmarcar **usar_ia**; a variável de repositório `PETNOVA_IA_ENABLED=false` desativa a preparação de IA nos agendamentos.

O workflow `Criar 2 conteudos diarios (demonstracao)` executa diariamente às **07:17 UTC**, prepara os dois conteúdos para 12:30 e 19:30 de **Europe/Lisbon**, verifica os ficheiros e simula as três redes. Os horários do calendário adaptam-se ao horário de verão; o cron é UTC. São horários de planeamento, **não publicações agendadas nas redes**.

Em **Actions → Criar 2 conteudos diarios → execução → Artifacts**, descarrega o pacote `petnova-conteudos-…`. Inclui vídeos, anúncios, textos, guiões, prompts opcionais e o relatório de simulação. A retenção é de sete dias. O exemplo no estúdio é fixo; não representa o último estado das execuções.

GitHub disponibiliza os runners padrão gratuitamente em repositórios públicos, dentro das suas regras. A execução pode atrasar; num repositório público sem atividade, os agendamentos podem ser desativados após 60 dias. O botão **Run workflow** permite iniciar uma preparação manualmente. Não há subscrições ou APIs pagas neste fluxo.

## Executar no Windows ou Linux

É necessário Python 3.11+, FFmpeg com `ffprobe` no PATH e uma fonte Arial/DejaVu Sans. O pacote `tzdata` suporta o fuso de Lisboa também no Windows.

```sh
python -m pip install -r requirements.txt
python scripts/sincronizar_catalogo.py --check
python automacao_conteudos.py
python scripts/validar_media.py
python scripts/simular_tudo.py
```

A saída fica em `conteudos/AAAA-MM-DD/`. Repetir no mesmo dia preserva textos revistos e alterações manuais. Se só existiam textos, uma execução posterior sem `--sem-video` acrescenta as imagens e os vídeos em falta.

```sh
# Sem renderização: textos e SRT; não cria MP4 nem PNG.
python automacao_conteudos.py --sem-video --saida conteudos-texto

# Testar uma data concreta.
python automacao_conteudos.py --dia 2026-10-21

# IA local: indicar um modelo que já esteja instalado no Ollama.
python automacao_conteudos.py --ia ollama --modelo NOME_DO_MODELO --saida conteudos-ia
```

O comando Python local não instala nem descarrega modelos automaticamente. O workflow GitHub prepara o modelo no seu ambiente temporário. Se o Ollama falhar, grava um aviso de fallback no manifesto e usa texto por modelo. Só são aceites ligações ao próprio computador; não há fallback para API paga. As sugestões de IA passam por validação limitada e continuam a exigir revisão humana.

Para geração diária num PC Windows, executa `scripts/agendar_windows.ps1` no PowerShell. Cria a tarefa **PetNova-Conteudos-Demo** às 09:15 da hora local do Windows, em simulação, para o utilizador atual. O PC precisa de estar ligado e de ter as dependências instaladas; o script não foi executado num Windows nesta sessão. Podes remover a tarefa pelo Agendador de Tarefas. Não é necessário usar esta opção se usares apenas o GitHub Actions.

## Ligar as redes mais tarde

Consulta [AUTOMACAO.md](AUTOMACAO.md). As credenciais pertencem a variáveis de ambiente do processo de publicação; nunca ao HTML, ao catálogo ou a um commit.

Para inspecionar um lote sem rede:

```sh
python scripts/publicar.py --manifest conteudos/AAAA-MM-DD/manifest.json --dry-run
```

Para marcar **um conteúdo já revisto** e só depois testar o envio real, quando as contas estiverem configuradas:

```sh
python scripts/publicar.py --manifest conteudos/AAAA-MM-DD/manifest.json --aprovar ID_DO_CONTEUDO
python scripts/publicar.py --manifest conteudos/AAAA-MM-DD/manifest.json --plataforma youtube --enviar
```

`--aprovar` não publica. `--enviar` não remove os bloqueios: a publicação tem de estar ativa em `config/automacao.json`, o conteúdo revisto e inalterado, os media presentes, o horário atingido e as credenciais configuradas. O SQLite em `state/` impede duplicados entre execuções. Não apagues esse estado: pedidos sem confirmação são bloqueados até verificar a conta.

O workflow diário **sempre simula** e não recebe credenciais. Uma rotina real futura pode usar `python scripts/rotina_diaria.py --enviar` num ambiente privado com estado persistente. A revisão é por conteúdo; não existe aprovação automática de novos rascunhos.

## Desenvolvimento e validação

```sh
python scripts/sincronizar_catalogo.py   # depois de editar produtos.csv
python -m unittest discover -s tests -v
node --check assets/store.js
python -m http.server 8765
```

O CSV é a fonte do catálogo. O JSON público é uma exportação validada. O frontend usa texto DOM, não insere HTML vindo do catálogo, e não inclui formulários pessoais, tracking publicitário ou integrações de pagamento.

Antes de vender é preciso confirmar fornecedores, características reais, direitos das imagens, preços, entregas e configurar um sistema de encomendas e pagamentos. Esta versão não pode ser transformada numa loja de vendas apenas mudando uma opção JSON.
