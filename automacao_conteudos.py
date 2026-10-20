"""Gera rascunhos de publicações a partir do catálogo demonstrativo.
Não publica automaticamente nem faz chamadas a IA externa.
Executar: python automacao_conteudos.py
"""
import csv
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parent
with (BASE / "produtos.csv").open(encoding="utf-8", newline="") as f:
    produtos = list(csv.DictReader(f))

saida = BASE / "conteudos"
saida.mkdir(exist_ok=True)
for produto in produtos:
    nome = produto["nome"]
    identificador = produto["id"]
    texto = f"""# {nome}

## Legenda para redes sociais
🐾 Conhece uma ideia para facilitar a rotina com o teu animal: {nome}.
A PetNova Portugal está em demonstração. Ainda não aceitamos encomendas.
#PetNovaPortugal #AnimaisDeEstimacao

## Guião de vídeo vertical (20–30 segundos)
Cena 1: Mostrar uma situação quotidiana relacionada com {nome}.
Cena 2: Apresentar o acessório, sem alegações de desempenho não verificadas.
Cena 3: Explicar a utilização de forma clara.
Cena 4: Terminar com «Conhece a PetNova Portugal — loja em demonstração».

## Revisão obrigatória antes de publicar
- Confirmar que o produto e as imagens podem ser usados comercialmente.
- Verificar alegações, preço, segurança e disponibilidade com fornecedor.
- Não afirmar que o produto foi testado se não foi.
"""
    (saida / f"produto_{identificador}.md").write_text(texto, encoding="utf-8")
print(f"Criados {len(produtos)} rascunhos em {saida} ({date.today()}).")
