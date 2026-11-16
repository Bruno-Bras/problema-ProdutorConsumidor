# Autoria, consultas e origem dos dados

**Dupla: Bruno Barros e Luana Barros.**

O projeto foi elaborado para este enunciado, com auxílio de IA (Codex) na geração
do código, documentação e automação. A dupla deve revisar e compreender a solução
e seguir as regras da disciplina sobre declaração de uso de IA. Não foram
copiados arquivos de implementação ou bases de dados de terceiros. Os slides e
o documento previamente existentes na pasta foram preservados, sem serem usados
como fonte de código ou incluídos no pacote.

## Referências oficiais para consulta e conferência

- Oracle, Java 17 — `Object`: contratos de `wait`, `notifyAll` e monitores:
  https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Object.html
- Oracle, Java 17 — `Thread`: criação, início, interrupção e `join`:
  https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Thread.html
- Oracle, Java Tutorials — blocos protegidos por condições (Guarded Blocks):
  https://docs.oracle.com/javase/tutorial/essential/concurrency/guardmeth.html
- Oracle, Java 17 — `CountDownLatch`, usado para coordenar o início:
  https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/CountDownLatch.html
- Oracle, Java 17 — `BitSet`, usado para verificar a identidade dos itens:
  https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/BitSet.html
- Python 3 — `subprocess`, `csv`, `statistics` e `unittest`, usados na automação:
  https://docs.python.org/3/library/subprocess.html
  https://docs.python.org/3/library/csv.html
  https://docs.python.org/3/library/statistics.html
  https://docs.python.org/3/library/unittest.html

## Gerador dos dados de teste

Não é necessário baixar arquivos de entrada. O gerador está no laço das threads
produtoras em `src/ProdutorConsumidor.java`: o produtor de índice `id` gera
`id, id+P, id+2P, ...`, enquanto o valor for menor que N. Isso cobre exatamente
os inteiros de 0 a N−1, sem repetição, inclusive quando N não é divisível por P.
Não há semente aleatória porque os valores são determinísticos. A intercalação
das threads é variável e depende do sistema operacional/JVM.

Os parâmetros dos seis experimentos e as repetições estão em
`scripts/experimentos.py`. Os casos adicionais estão em `testes/testar.py`.
Os CSVs são **saídas de execuções reais**, geradas pelo script, e não arquivos
de entrada. O ambiente e o hash da fonte medida acompanham esses resultados.
