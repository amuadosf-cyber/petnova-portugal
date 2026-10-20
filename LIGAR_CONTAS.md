# Ligar as contas existentes da PetNova

A preparação diária de conteúdos funciona no GitHub mesmo com o computador desligado. A ligação às contas fica para a sessão de configuração no PC. Até lá, a loja mantém o carrinho de demonstração e os conteúdos ficam como rascunhos.

## Quando estiveres no PC

1. Abre a pasta do projeto e executa **Verificar-PetNova.bat**. Em alternativa, usa `python scripts/verificar_configuracao.py`. O diagnóstico só lê a configuração deste computador e mostra quais os componentes disponíveis.
2. Identifica o canal YouTube existente da PetNova pelo seu link ou @. O link identifica o canal; a publicação precisa também da autorização OAuth da conta correta.
3. Segue a secção **YouTube** em [AUTOMACAO.md](AUTOMACAO.md) para configurar a aplicação e autorizar o envio. Os valores privados pertencem ao processo de publicação; o diagnóstico mostra apenas se estão presentes.
4. Depois do teste privado do YouTube, segue a secção **Instagram**, incluindo o alojamento HTTPS dos vídeos. Os conteúdos para TikTok são preparados para publicação nativa.

As autorizações são concluídas no serviço correspondente. Os primeiros testes de publicação devem usar um rascunho revisto. O diagnóstico não valida tokens com as plataformas e não ativa a publicação.

## Verificação técnica

```sh
python scripts/verificar_configuracao.py --json
```

O resultado contém apenas indicadores de presença das credenciais. A tarefa Windows e a autenticação real continuam por testar num PC Windows e com as contas autorizadas.
