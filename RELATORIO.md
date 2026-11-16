# Relatório de experimentos — Produtor x Consumidor

**Dupla: Bruno Barros e Luana Barros**

## Objetivo e implementação

Verificar uma solução do problema Produtor x Consumidor com P produtores, C
consumidores e um buffer circular de capacidade T. A implementação usa threads
reais da JVM, exclusão mútua com `synchronized` e espera condicional com `wait()`
e `notifyAll()`. Não utiliza uma fila concorrente pronta.

## Método

Foram usados P=C=10, P=10/C=5 e P=5/C=10, cada um com T=1 e T=20 (>10).
Cada execução gera **20000 itens no total**, independentemente de P: inteiros
únicos de 0 a 19999. Não há arquivos de entrada nem aleatoriedade nos valores.
A distribuição e a ordem de execução das threads dependem do escalonador.

Cada cenário foi exercitado uma vez antes da coleta e medido 5 vezes,
totalizando 30 execuções medidas. Cada execução inicia uma JVM nova;
a execução preliminar **não** representa aquecimento de JIT da JVM seguinte.
Os cenários são executados na ordem apresentada na tabela. Os atrasos artificiais
são zero, e o log por operação fica desativado. O script impõe limite de 60 s
por processo e interrompe a coleta em caso de falha.

O cronômetro usa `System.nanoTime()` desde a liberação conjunta das threads já
criadas até o retorno dos `join()`. Inclui escalonamento, sincronização,
processamento, auditoria por item e encerramento. Exclui compilação, criação das
threads, inicialização da JVM, auditoria final e impressão do resumo. O auditor
também usa um bloqueio; portanto, estes tempos representam o programa didático
com verificação habilitada, não o custo isolado do buffer.

## Resultados medidos

Tempos em milissegundos. O desvio é o desvio padrão amostral das cinco execuções.

| P | C | T | Média (ms) | Mediana (ms) | Desvio (ms) | Consistência em todas |
|---|---|---|---|---|---|---|
| 10 | 10 | 1 | 1201.663 | 1207.654 | 140.208 | SIM |
| 10 | 10 | 20 | 159.914 | 165.453 | 14.096 | SIM |
| 10 | 5 | 1 | 1206.519 | 1272.049 | 204.603 | SIM |
| 10 | 5 | 20 | 113.770 | 111.364 | 6.901 | SIM |
| 5 | 10 | 1 | 1246.415 | 1099.021 | 357.120 | SIM |
| 5 | 10 | 20 | 139.869 | 139.321 | 8.636 | SIM |

Em todas as 30 execuções, a auditoria confirmou 20000 itens consumidos,
20000 identificadores distintos, zero duplicados, zero identificadores inválidos
e buffer vazio ao final. A ocupação máxima observada não ultrapassou T.
A auditoria verifica a identidade dos itens, além de comparar contagens.

## Discussão

T=1 exige alternância frequente entre inserir e retirar: só cabe um item por vez.
T=20 permite acumular até vinte itens, absorvendo pequenos desequilíbrios entre
produção e consumo. Ter mais produtores ou consumidores não garante menor tempo:
o bloqueio do buffer é compartilhado, `notifyAll()` pode acordar várias threads
que voltarão a esperar, e o escalonador influencia as medições.

As relações P=2C e C=2P mudam também a quantidade total de threads em relação a
P=C=10. Logo, a comparação não isola apenas a proporção entre produtores e
consumidores. Os valores são observações locais de uma carga sintética pequena,
sem trabalho computacional relevante por item. Cinco repetições, JVMs novas,
ordem fixa dos cenários e atividade concorrente da máquina limitam conclusões de
desempenho. A ausência de erros nessas execuções é evidência experimental; a
justificativa da sincronização está nas invariantes explicadas no README.

## Conclusão

A implementação atendeu às configurações solicitadas e preservou os itens em
todas as execuções medidas. O programa encerrou após todos os produtores
terminarem e todos os itens serem consumidos, inclusive com buffer unitário.
Não há garantia de distribuição igual do trabalho ou de justiça entre threads.

## Reproduzir e conferir

Na raiz do projeto: `python3 scripts/experimentos.py`.
Esse comando substitui os resultados anteriores por uma nova coleta.
Dados individuais: `resultados/execucoes.csv`; agregados: `resultados/resumo.csv`.
Ambiente e hash do código medido: `resultados/ambiente.txt`.
Referências e origem dos dados: `FONTES.md`.
