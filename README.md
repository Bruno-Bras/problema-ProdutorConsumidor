# Trabalho prático — Multithreading: Produtor x Consumidor

**Dupla: Bruno Barros e Luana Barros**  
Linguagem: Java 17 ou superior, sem bibliotecas externas.

## 1. Comece por aqui

O programa cria P threads produtoras e C threads consumidoras. Elas compartilham
um buffer circular de capacidade T. Cada produtor gera parte dos números de 0
até N−1; os consumidores retiram os números e registram o processamento. N é a
quantidade **total** de itens da execução, não a quantidade por produtor.

Java foi escolhido por oferecer threads reais, monitores e ferramentas de
compilação padrão, além de permitir mostrar explicitamente a sincronização.

No Linux, abra um terminal e execute:

```bash
cd /home/brunodev/Documentos/SO-ESST
java -version
javac -version
bash executar.sh --produtores 2 --consumidores 2 --buffer 1 --itens 10 --log
```

É necessário um **JDK**, que contém `java` e `javac`. Um JRE sozinho não basta.
No Ubuntu/Debian, caso falte o compilador, instale o JDK:

```bash
sudo apt update
sudo apt install openjdk-17-jdk
```

O script compila o código e inicia o programa. Os arquivos compilados vão para
`build/`, que pode ser apagada e será recriada. A execução não precisa de internet.
O caminho no comando `cd` pode ser ajustado se o projeto for movido.

Também é possível compilar e executar manualmente, sem o script:

```bash
mkdir -p build
javac -encoding UTF-8 --release 17 -d build src/ProdutorConsumidor.java
java -cp build ProdutorConsumidor --produtores 10 --consumidores 5 --buffer 20 --itens 20000
```

No Windows, use `mkdir build` no lugar de `mkdir -p build`; os comandos `javac` e
`java` são os mesmos. Na IDE, abra `src/ProdutorConsumidor.java`, configure JDK 17
ou superior e execute seu método `main`. Os parâmetros podem ser definidos na
configuração de execução da IDE. Este é um programa de console Java, sem Android.

## 2. Parâmetros configuráveis

| Opção | Significado | Padrão |
|---|---|---|
| `--produtores P` | Número de threads produtoras; P > 0 | 2 |
| `--consumidores C` | Número de threads consumidoras; C > 0 | 2 |
| `--buffer T` | Quantidade máxima de itens guardados; T > 0 | 5 |
| `--itens N` | Quantidade total de itens; N ≥ 0 | 20 |
| `--atraso-prod-ms MS` | Pausa antes de produzir cada item; MS ≥ 0 | 0 |
| `--atraso-cons-ms MS` | Pausa ao processar cada item; MS ≥ 0 | 0 |
| `--log` | Exibe cada inserção/retirada | desativado |
| `--help` | Mostra o modo de uso | — |

As opções com valor aceitam inteiros de 32 bits. Use quantidades compatíveis com
a memória e os limites de threads da máquina. A pausa em milissegundos é uma
simulação: sua duração efetiva depende do escalonador.

Para acompanhar lentamente as operações:

```bash
bash executar.sh --produtores 2 --consumidores 1 --buffer 3 --itens 12 --atraso-prod-ms 50 --atraso-cons-ms 100 --log
```

O log pode mostrar itens fora da ordem numérica: produtores diferentes são
escalonados em momentos diferentes. O buffer preserva a ordem de **inserção**
(FIFO), que não precisa ser a ordem 0, 1, 2... O processamento pode terminar em
outra ordem quando há vários consumidores.

## 3. Como o código funciona, passo a passo

Todo o código principal está em `src/ProdutorConsumidor.java`, dividido em partes:

1. **Config** lê os parâmetros e rejeita configurações inválidas.
2. **Buffer** contém um vetor de tamanho T, dois índices e a ocupação atual.
   `fim` aponta a próxima inserção e `inicio` aponta a próxima retirada.
   O cálculo `(indice + 1) % capacidade` faz os índices voltarem ao começo.
3. **Produtores** dividem os dados por índice. Com P=2 e N=6, o produtor 1 gera
   0, 2 e 4; o produtor 2 gera 1, 3 e 5. A soma é N, sem sobreposição.
4. **Consumidores** retiram um item e registram seu processamento no auditor.
   Os atrasos de processamento ficam fora do bloqueio do buffer.
5. **Auditor** usa `BitSet` para marcar os identificadores recebidos e detectar
   duplicados, itens inválidos e ausentes. Seu próprio acesso também é sincronizado.
6. **Coordenação** cria todas as threads, espera que estejam prontas e libera um
   `CountDownLatch` comum. O programa principal espera o término com `join()`.
7. **Resumo** apresenta as contagens, o tempo e o resultado da auditoria.

### Por que a sincronização mantém a consistência

`inserir`, `retirar`, `finalizarProdutor` e `cancelar` são métodos `synchronized`
do **mesmo objeto Buffer**. Apenas uma thread por vez executa essas operações.
Assim, verificar a condição e alterar vetor, índices e ocupação é uma operação
protegida: duas threads não escrevem na mesma vaga ao mesmo tempo.

As invariantes são `0 ≤ quantidade ≤ T` e índices dentro do vetor. Só se insere
quando existe vaga; só se retira quando existe item. O estado começa vazio e cada
operação protegida preserva essas condições.

Quando o buffer está cheio, o produtor chama `wait()`. Quando está vazio e ainda
há produtores ativos, o consumidor chama `wait()`. Essa chamada **libera o monitor**:
outras threads podem entrar e mudar o estado. Ao acordar, a thread readquire o
monitor e reavalia a condição em um `while`. Usar `if` seria incorreto, pois outra
thread pode usar o item/vaga primeiro e existem despertares espúrios.

Depois de inserir ou retirar, `notifyAll()` acorda as threads à espera. Elas
competem novamente pelo monitor e verificam suas condições. Como produtores e
consumidores compartilham o conjunto de espera, acordar todas evita depender de
`notify()` escolher uma thread do tipo que consegue prosseguir. Há custo por
acordar threads que voltarão a dormir. Não há espera ocupada nem pausas usadas
como mecanismo de sincronização.

### Como termina sem deixar consumidores presos

O buffer mantém a quantidade de produtores ainda ativos. Cada produtor a reduz
em um bloco `finally` e notifica as threads que aguardam. O consumidor só recebe
`null` quando o buffer está vazio **e** nenhum produtor continua ativo. `null` é
sinal de término; não ocupa uma posição no vetor. Desse modo, nenhum item fica
para trás e não são necessárias sentinelas por consumidor. N=0 também encerra.

Falhas em uma thread são comunicadas ao coordenador e cancelam o buffer,
acordando as demais. O programa devolve código de saída 0 no sucesso, 2 em erro
de configuração e 1 em falha de execução. O uso de `join()` garante ao programa
principal a visibilidade dos resultados das threads terminadas. Não há garantia
de justiça ou de quantidades iguais de itens por consumidor; o encerramento
normal pressupõe que o escalonador permita progresso às threads.

## 4. Como interpretar a saída

Uma linha como `Produtor-1 produziu 0 | buffer=1/3` significa que o produtor 1
inseriu o item 0 e o buffer passou a ter uma posição ocupada de três disponíveis.
A linha final usa os seguintes campos:

| Campo | Significado |
|---|---|
| `P`, `C`, `T`, `itens` | Configuração utilizada |
| `consumidos` | Total de itens processados |
| `unicos` | Quantidade de identificadores distintos válidos |
| `repetidos`, `invalidos` | Erros de identidade detectados |
| `restantes` | Ocupação do buffer ao terminar; deve ser zero |
| `pico` | Maior ocupação observada; nunca deve exceder T |
| `esperas_prod`, `esperas_cons` | Número de chamadas a `wait()` por tipo de thread |
| `tempo_ms` | Tempo desde a liberação das threads até seu término |
| `status` | `OK` se a auditoria e o estado final forem consistentes |

As esperas não medem duração nem quantidade de threads distintas; uma thread
pode esperar muitas vezes. O log torna a execução mais lenta: use-o para explicar
o funcionamento e desative-o nas medições. `status=OK` exige N consumidos, N
identificadores distintos, zero duplicados/inválidos e buffer vazio no final.

## 5. Experimentos pedidos no enunciado

| Relação | P | C | Capacidades T |
|---|---|---|---|
| Mesma quantidade: P=C | 10 | 10 | 1 e 20 |
| Dobro de produtores: P=2C | 10 | 5 | 1 e 20 |
| Dobro de consumidores: C=2P | 5 | 10 | 1 e 20 |

Para executar uma configuração manualmente, por exemplo:

```bash
bash executar.sh --produtores 10 --consumidores 10 --buffer 1 --itens 20000
bash executar.sh --produtores 10 --consumidores 10 --buffer 20 --itens 20000
bash executar.sh --produtores 10 --consumidores 5 --buffer 1 --itens 20000
bash executar.sh --produtores 10 --consumidores 5 --buffer 20 --itens 20000
bash executar.sh --produtores 5 --consumidores 10 --buffer 1 --itens 20000
bash executar.sh --produtores 5 --consumidores 10 --buffer 20 --itens 20000
```

A coleta automática requer Python 3.9 ou superior, sem pacotes adicionais:

```bash
python3 scripts/experimentos.py
```

Esse comando compila o programa, executa uma rodada preliminar por cenário e
cinco repetições medidas por cenário, valida os resultados e **substitui**:

- `resultados/execucoes.csv`: todas as 30 medições individuais.
- `resultados/resumo.csv`: média, mediana, desvio amostral, mínimo e máximo.
- `resultados/ambiente.txt`: ambiente, data e hash do código medido.
- `RELATORIO.md`: método, tabela real, discussão e conclusão.

Os resultados já coletados acompanham a entrega. O tempo varia de uma máquina
ou execução para outra. Consulte o relatório para conhecer os limites da comparação.
Os experimentos não precisam ser executados para demonstrar o programa.

## 6. Testes automáticos

```bash
python3 testes/testar.py
```

Os testes verificam os seis cenários, término com zero itens, mais threads que
itens, produtor lento, consumidor lento, ordem FIFO/ocupação pelo log, rejeição
de argumentos inválidos e repetição do encerramento com buffer unitário. Cada
processo tem um tempo limite, de modo que um travamento provoca falha no teste.
A saída da verificação realizada está em `resultados/testes.txt`.

## 7. Roteiro simples para apresentar e entregar

1. Apresente os nomes da dupla e explique o papel de P, C, T e N.
2. Execute o exemplo de 10 itens com `--log` da seção 1.
3. Mostre os métodos `inserir()` e `retirar()` e explique o monitor e seus `while`.
4. Explique por que o consumidor espera quando está vazio e como sabe que acabou.
5. Mostre `RELATORIO.md` e os seis cenários medidos.
6. Execute os testes para demonstrar as verificações de consistência.
7. Entregue `entrega_produtor_consumidor.zip`, disponível nesta pasta.

O ZIP contém código, documentação, scripts e resultados; os slides e o documento
que já estavam nesta pasta foram preservados e não fazem parte do pacote.
Para refazer o pacote depois de modificar código ou resultados:

```bash
python3 scripts/empacotar.py
```

Antes de entregar, a dupla deve ler o código e conseguir explicar o monitor,
as condições de espera e a estratégia de encerramento. A origem do código, dos
dados sintéticos e as fontes de consulta estão documentadas em `FONTES.md`.
