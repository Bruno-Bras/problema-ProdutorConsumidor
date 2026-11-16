/*
 * Trabalho prático de Sistemas Operacionais — Produtor x Consumidor.
 * Dupla: Bruno Barros e Luana Barros.
 * Implementação didática original desta entrega, elaborada com auxílio de IA.
 * Referências de APIs e conceitos: ver FONTES.md.
 * Dados sintéticos: inteiros de 0 até N-1, gerados no próprio código.
 */
import java.util.BitSet;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;

public final class ProdutorConsumidor {
    /** Monitor: todos os campos do buffer são acessados com o mesmo bloqueio. */
    static final class Buffer {
        private final int[] fila;
        private int inicio, fim, quantidade, produtoresAtivos, pico;
        private long esperasProdutor, esperasConsumidor;
        private boolean cancelado;
        private final boolean log;

        Buffer(int capacidade, int produtores, boolean log) {
            fila = new int[capacidade];
            produtoresAtivos = produtores;
            this.log = log;
        }

        synchronized void inserir(int item) throws InterruptedException {
            // while é obrigatório: outra thread pode ocupar a vaga antes de nós,
            // e wait também pode retornar sem uma notificação (despertar espúrio).
            while (quantidade == fila.length && !cancelado) {
                esperasProdutor++;
                wait(); // libera o monitor enquanto espera; readquire ao retornar.
            }
            verificarCancelamento();
            fila[fim] = item;
            fim = (fim + 1) % fila.length;
            quantidade++;
            pico = Math.max(pico, quantidade);
            registrar("produziu", item);
            notifyAll(); // podem existir consumidores esperando por um item.
        }

        synchronized Integer retirar() throws InterruptedException {
            while (quantidade == 0 && produtoresAtivos > 0 && !cancelado) {
                esperasConsumidor++;
                wait();
            }
            verificarCancelamento();
            // Só termina quando não haverá mais produção E a fila foi esvaziada.
            if (quantidade == 0) return null;
            int item = fila[inicio];
            inicio = (inicio + 1) % fila.length;
            quantidade--;
            registrar("consumiu", item);
            notifyAll(); // podem existir produtores esperando por uma vaga.
            return item;
        }

        synchronized void finalizarProdutor() {
            produtoresAtivos--;
            notifyAll(); // acorda consumidores, inclusive após a última produção.
        }

        synchronized void cancelar() {
            cancelado = true;
            notifyAll();
        }

        private void verificarCancelamento() throws InterruptedException {
            if (cancelado) throw new InterruptedException("Execução cancelada");
        }

        private void registrar(String acao, int item) {
            // Log dentro do monitor: mostra a ocupação associada à operação.
            if (log) System.out.printf("%s %s %d | buffer=%d/%d%n",
                    Thread.currentThread().getName(), acao, item, quantidade, fila.length);
        }
    }

    /** Auditor independente: detecta itens inválidos, repetidos ou ausentes. */
    static final class Auditor {
        private final BitSet vistos;
        private final int total;
        private int consumidos, repetidos, invalidos;
        Auditor(int total) { this.total = total; vistos = new BitSet(total); }
        synchronized void registrar(int item) {
            consumidos++;
            if (item < 0 || item >= total) invalidos++;
            else if (vistos.get(item)) repetidos++;
            else vistos.set(item);
        }
        boolean valido() {
            // Chamado após join: todas as escritas das threads estão visíveis.
            return consumidos == total && vistos.cardinality() == total
                    && repetidos == 0 && invalidos == 0;
        }
    }

    record Config(int p, int c, int t, int itens, int atrasoP, int atrasoC, boolean log) {
        static Config ler(String[] args) {
            int p = 2, c = 2, t = 5, n = 20, dp = 0, dc = 0;
            boolean log = false;
            for (int i = 0; i < args.length; i++) {
                String chave = args[i];
                if (chave.equals("--log")) { log = true; continue; }
                if (!java.util.Set.of("--produtores", "--consumidores", "--buffer",
                        "--itens", "--atraso-prod-ms", "--atraso-cons-ms").contains(chave))
                    throw new IllegalArgumentException("Opção desconhecida: " + chave);
                if (++i >= args.length) throw new IllegalArgumentException("Falta valor para " + chave);
                int valor = Integer.parseInt(args[i]);
                switch (chave) {
                    case "--produtores" -> p = valor;
                    case "--consumidores" -> c = valor;
                    case "--buffer" -> t = valor;
                    case "--itens" -> n = valor;
                    case "--atraso-prod-ms" -> dp = valor;
                    case "--atraso-cons-ms" -> dc = valor;
                }
            }
            if (p <= 0 || c <= 0 || t <= 0 || n < 0 || dp < 0 || dc < 0)
                throw new IllegalArgumentException("P, C e T devem ser positivos; itens e atrasos não negativos.");
            return new Config(p, c, t, n, dp, dc, log);
        }
    }

    @FunctionalInterface interface Tarefa { void executar() throws Exception; }

    static Thread criar(String nome, Tarefa tarefa, Buffer buffer,
                        AtomicReference<Throwable> falha, CountDownLatch prontos,
                        CountDownLatch inicio) {
        return new Thread(() -> {
            prontos.countDown();
            try { inicio.await(); tarefa.executar(); }
            catch (Throwable erro) {
                falha.compareAndSet(null, erro);
                buffer.cancelar(); // libera threads bloqueadas em caso de falha.
            }
        }, nome);
    }

    static void executar(Config cfg) throws InterruptedException {
        Buffer buffer = new Buffer(cfg.t, cfg.p, cfg.log);
        Auditor auditor = new Auditor(cfg.itens);
        AtomicReference<Throwable> falha = new AtomicReference<>();
        CountDownLatch prontos = new CountDownLatch(Math.addExact(cfg.p, cfg.c));
        CountDownLatch inicio = new CountDownLatch(1);
        Thread[] threads = new Thread[Math.addExact(cfg.p, cfg.c)];
        for (int p = 0; p < cfg.p; p++) {
            final int id = p;
            threads[p] = criar("Produtor-" + (p + 1), () -> {
                try {
                    // Partição sem sobreposição: produtor id gera id, id+P, id+2P...
                    // long evita overflow no incremento; N é o total, não por produtor.
                    for (long item = id; item < cfg.itens; item += cfg.p) {
                        if (cfg.atrasoP > 0) Thread.sleep(cfg.atrasoP);
                        buffer.inserir((int) item);
                    }
                } finally { buffer.finalizarProdutor(); }
            }, buffer, falha, prontos, inicio);
        }
        for (int c = 0; c < cfg.c; c++) {
            threads[cfg.p + c] = criar("Consumidor-" + (c + 1), () -> {
                Integer item;
                while ((item = buffer.retirar()) != null) {
                    // Processamento fora do monitor: não prende o buffer durante sleep.
                    if (cfg.atrasoC > 0) Thread.sleep(cfg.atrasoC);
                    auditor.registrar(item);
                }
            }, buffer, falha, prontos, inicio);
        }
        long comeco;
        try {
            for (Thread thread : threads) thread.start();
            prontos.await();
            comeco = System.nanoTime();
            inicio.countDown();
            for (Thread thread : threads) thread.join();
        } catch (Throwable erro) {
            buffer.cancelar();
            for (Thread thread : threads) thread.interrupt();
            for (Thread thread : threads) thread.join();
            throw erro;
        }
        double ms = (System.nanoTime() - comeco) / 1_000_000.0;
        if (falha.get() != null) throw new IllegalStateException("Falha em uma thread", falha.get());
        boolean ok = auditor.valido() && buffer.quantidade == 0
                && buffer.produtoresAtivos == 0 && buffer.pico <= cfg.t;
        System.out.printf(Locale.ROOT,
                "P=%d C=%d T=%d itens=%d consumidos=%d unicos=%d repetidos=%d invalidos=%d "
                + "restantes=%d pico=%d esperas_prod=%d esperas_cons=%d tempo_ms=%.3f status=%s%n",
                cfg.p, cfg.c, cfg.t, cfg.itens, auditor.consumidos, auditor.vistos.cardinality(),
                auditor.repetidos, auditor.invalidos, buffer.quantidade, buffer.pico,
                buffer.esperasProdutor, buffer.esperasConsumidor, ms, ok ? "OK" : "FALHA");
        if (!ok) throw new IllegalStateException("Inconsistência detectada na auditoria");
    }

    public static void main(String[] args) {
        if (java.util.Arrays.asList(args).contains("--help")) {
            return;
        }
        try { executar(Config.ler(args)); }
        catch (IllegalArgumentException erro) {
            System.err.println("Configuração inválida: " + erro.getMessage());
            System.exit(2);
        } catch (Exception erro) {
            erro.printStackTrace();
            System.exit(1);
        }
    }
}
