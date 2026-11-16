#!/usr/bin/env python3
"""Bruno Barros e Luana Barros. Gera dados, executa cenários e resume medições reais.
Sem pacotes externos. Não lê arquivos de entrada: o gerador está no código Java.
"""
import csv
import datetime
import hashlib
import platform
import statistics
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CENARIOS = [(10, 10, 1), (10, 10, 20), (10, 5, 1), (10, 5, 20),
            (5, 10, 1), (5, 10, 20)]
ITENS = 20_000
REPETICOES = 5


def executar(p, c, t):
    comando = ['java', '-cp', 'build', 'ProdutorConsumidor', '--produtores', str(p),
               '--consumidores', str(c), '--buffer', str(t), '--itens', str(ITENS)]
    processo = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True,
                              check=True, timeout=60)
    valores = dict(par.split('=', 1) for par in processo.stdout.strip().split())
    assert valores['status'] == 'OK', valores
    for chave in ('itens', 'consumidos', 'unicos'):
        assert int(valores[chave]) == ITENS, valores
    for chave in ('repetidos', 'invalidos', 'restantes'):
        assert int(valores[chave]) == 0, valores
    assert 0 < int(valores['pico']) <= t, valores
    return valores


def main():
    subprocess.run(['javac', '-encoding', 'UTF-8', '--release', '17', '-d', 'build',
                    'src/ProdutorConsumidor.java'], cwd=RAIZ, check=True)
    saida = RAIZ / 'resultados'
    saida.mkdir(exist_ok=True)
    linhas = []
    for p, c, t in CENARIOS:
        # Cada execução usa nova JVM. Esta rodada preliminar não aquece as JVMs
        # medidas; apenas exercita o cenário antes da coleta.
        executar(p, c, t)
        for repeticao in range(1, REPETICOES + 1):
            linha = executar(p, c, t)
            linha = {'repeticao': repeticao, **linha}
            linhas.append(linha)
        print(f'Concluído: P={p}, C={c}, T={t}', flush=True)
    with (saida / 'execucoes.csv').open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    resumos = []
    for p, c, t in CENARIOS:
        grupo = [r for r in linhas if (int(r['P']), int(r['C']), int(r['T'])) == (p, c, t)]
        tempos = [float(r['tempo_ms']) for r in grupo]
        resumos.append(dict(P=p, C=c, T=t, repeticoes=REPETICOES, itens=ITENS,
                            media_ms=round(statistics.mean(tempos), 3),
                            mediana_ms=round(statistics.median(tempos), 3),
                            desvio_amostral_ms=round(statistics.stdev(tempos), 3),
                            minimo_ms=min(tempos), maximo_ms=max(tempos),
                            todas_consistentes='SIM'))
    with (saida / 'resumo.csv').open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(resumos[0]))
        escritor.writeheader()
        escritor.writerows(resumos)
    java = subprocess.run(['java', '-version'], capture_output=True, text=True, check=True)
    fonte_hash = hashlib.sha256((RAIZ / 'src/ProdutorConsumidor.java').read_bytes()).hexdigest()
    ambiente = f'''Data: {datetime.datetime.now().astimezone().isoformat()}
Sistema: {platform.platform()}
Máquina: {platform.machine()}
Processador: {platform.processor() or 'não informado por platform.processor'}
Java:
{java.stderr or java.stdout}
SHA-256 de src/ProdutorConsumidor.java: {fonte_hash}
'''
    if Path('/proc/cpuinfo').exists():
        for linha in Path('/proc/cpuinfo').read_text().splitlines():
            if linha.startswith('model name'):
                ambiente += 'CPU: ' + linha.split(':', 1)[1].strip() + '\n'
                break
    (saida / 'ambiente.txt').write_text(ambiente, encoding='utf-8')
    tabela = '\n'.join(f"| {r['P']} | {r['C']} | {r['T']} | {r['media_ms']:.3f} | "
                        f"{r['mediana_ms']:.3f} | {r['desvio_amostral_ms']:.3f} | SIM |" for r in resumos)
    relatorio = f'''# Relatório de experimentos — Produtor x Consumidor

**Dupla: Bruno Barros e Luana Barros**

## Objetivo e implementação

Verificar uma solução do problema Produtor x Consumidor com P produtores, C
consumidores e um buffer circular de capacidade T. A implementação usa threads
reais da JVM, exclusão mútua com `synchronized` e espera condicional com `wait()`
e `notifyAll()`. Não utiliza uma fila concorrente pronta.

## Método

Foram usados P=C=10, P=10/C=5 e P=5/C=10, cada um com T=1 e T=20 (>10).
Cada execução gera **{ITENS} itens no total**, independentemente de P: inteiros
únicos de 0 a {ITENS - 1}. Não há arquivos de entrada nem aleatoriedade nos valores.
A distribuição e a ordem de execução das threads dependem do escalonador.

Cada cenário foi exercitado uma vez antes da coleta e medido {REPETICOES} vezes,
totalizando {len(linhas)} execuções medidas. Cada execução inicia uma JVM nova;
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
{tabela}

Em todas as {len(linhas)} execuções, a auditoria confirmou {ITENS} itens consumidos,
{ITENS} identificadores distintos, zero duplicados, zero identificadores inválidos
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
'''
    (RAIZ / 'RELATORIO.md').write_text(relatorio, encoding='utf-8')


if __name__ == '__main__':
    main()
