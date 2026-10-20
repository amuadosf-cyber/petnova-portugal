# Automação de conteúdos PetNova

## O que funciona sem contas

Python + Pillow + FFmpeg criam os anúncios, vídeos gráficos, legendas, guiões e calendário. GitHub Actions prepara um lote por dia em ambiente Linux, sem depender do teu computador. Não precisa de tokens nem envia conteúdo às plataformas.

Ollama é opcional e corre localmente. Esta integração pede apenas um título em JSON; os avisos de demonstração, descrições e chamadas para conhecer o projeto usam texto controlado. Um modelo local, a sua licença, requisitos de memória e consumo do computador devem ser verificados antes da instalação. O resto da pipeline funciona sem ele.

## YouTube

1. Criar um projeto no Google Cloud, ativar YouTube Data API v3 e configurar o consentimento OAuth.
2. Autorizar a conta do canal usando OAuth e o âmbito `https://www.googleapis.com/auth/youtube.upload`; obter um refresh token por um fluxo oficial adequado ao cliente. Não enviar passwords ou tokens por chat.
3. No processo privado que irá publicar, definir `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` e `YOUTUBE_REFRESH_TOKEN`.
4. Manter inicialmente `publishing.youtube_privacy` como `private` e testar um conteúdo revisto. A política e a verificação da aplicação continuam a aplicar-se.
5. Só depois configurar a visibilidade pretendida. Sem configuração explícita, este adaptador nunca pede visibilidade pública.

A implementação renova o token, inicia a sessão de upload e envia o MP4. Só regista sucesso ao receber um ID. Uma resposta incerta fica bloqueada para evitar novo upload. Não continua automaticamente uma sessão interrompida; verifica primeiro o YouTube Studio.

A escolha `containsSyntheticMedia=false` aplica-se aos atuais cartões gráficos, sem representação realista de acontecimentos ou pessoas. Se trocares o renderizador por filmagens sintéticas realistas, revê a divulgação de conteúdo sintético e os metadados antes de publicar.

## Instagram

1. Usar uma conta profissional (Business ou Creator) e uma aplicação Meta com Instagram Login.
2. Obter as permissões e token aplicáveis, incluindo `instagram_business_basic` e `instagram_business_content_publish`, segundo a documentação atual e o estado da aplicação.
3. Definir `IG_USER_ID` e `IG_ACCESS_TOKEN` como variáveis de ambiente privadas.
4. Definir `publishing.instagram_api_version` para uma versão Graph API suportada pela tua aplicação. Está vazia de propósito; os testes usam uma versão simulada, não validam uma conta real.
5. Disponibilizar cada MP4 num endereço HTTPS público que o Instagram consiga obter. Preencher `post.media.public_video_url` no manifesto antes da revisão, ou configurar `publishing.public_media_base` com a pasta pública daquele lote diário. A estrutura abaixo dessa base tem de corresponder a `post.media.video`.

Os ficheiros do GitHub Actions não são URLs públicos de vídeo apropriados para este envio. A geração diária não faz upload para um host de media. O vídeo de exemplo na loja é uma amostra fixa, não deve ser reutilizado como URL de todos os posts.

O adaptador cria um contentor REELS, consulta o processamento e só chama `media_publish` quando recebe `FINISHED`. Token expirado, conta incompatível, quotas e falhas de processamento impedem o envio. A renovação de tokens Instagram ainda não está automatizada; usa o fluxo oficial e acompanha a validade.

## TikTok

Estão prontos MP4, PNG, texto e SRT para publicação ou agendamento pela interface nativa do TikTok. Ainda não existe uma ligação à conta.

O Direct Post da TikTok exige uma integração aprovada, controlo explícito do criador e apresentação das opções atuais da conta. As regras também excluem uma ferramenta interna dedicada apenas a carregar conteúdos para as contas da própria equipa. Por isso esta automação não implementa um publicador Direct Post privado nem tenta contornar a revisão. A API Upload disponibiliza um fluxo em que o utilizador termina a publicação na app; não foi integrada nesta versão.

Na publicação nativa, revê o vídeo, a legenda, a divulgação de conteúdo promocional da própria marca e quaisquer indicações de conteúdo gerado por IA exigidas para os materiais usados.

## Ativação e estado persistente

A configuração do carrinho fica em demonstração. A opção `publishing.enabled` é independente: permite divulgar o projeto mantendo as vendas desativadas. A alteração dessa opção não liga contas nem publica por si só.

Cada conteúdo tem de ser revisto usando `scripts/publicar.py --aprovar ID`. A revisão guarda um hash do manifesto, vídeo e anúncio. Editar os textos, o URL de media ou os ficheiros invalida a revisão. Após o horário de Lisboa e com as credenciais configuradas, `--plataforma youtube --enviar` ou `--plataforma instagram --enviar` pode efetuar uma publicação real.

`state/publications.sqlite3` regista a combinação de ID e plataforma antes do pedido. Sucesso, pedido pendente e resposta incerta impedem reenvios automáticos. Mantém esse ficheiro no mesmo ambiente entre execuções. Em caso de falha, verifica primeiro se a plataforma recebeu o vídeo; não apagues entradas para forçar tentativas sem essa verificação.

A rotina `scripts/rotina_diaria.py` gera o dia uma vez e percorre a fila já existente. Por defeito só simula; com `--enviar` tenta YouTube e Instagram, respeitando revisão, credenciais e horários. Para publicação pontual, chama a rotina depois dos horários planeados. Não é um serviço residente. A tarefa Windows fornecida só agenda a preparação/simulação diária; uma agenda de envio real deverá ser configurada depois dos testes com as contas.

## Fontes oficiais verificadas em 20 de outubro de 2026

- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [YouTube OAuth para aplicações instaladas](https://developers.google.com/youtube/data/guides/auth/installed-apps)
- [YouTube videos.insert](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
- [YouTube uploads retomáveis](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol)
- [Instagram Content Publishing](https://developers.facebook.com/documentation/instagram-platform/content-publishing)
- [Coleção oficial Meta Instagram](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [TikTok Content Sharing Guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines)
- [TikTok Upload](https://developers.tiktok.com/docs/en/content-posting-api-reference-upload-video)
- [Agendamentos GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Faturação GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Limites, permissões e planos podem mudar. Nenhum envio real ou autenticação nestas três redes foi testado nesta sessão. Os testes de integração usam respostas simuladas; a renderização de anúncios e MP4 foi executada de verdade.
