#!/usr/bin/env python3
"""Testes de integração. Dupla: Bruno Barros e Luana Barros."""
import re
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class Testes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['javac', '-encoding', 'UTF-8', '--release', '17', '-d', 'build',
                        'src/ProdutorConsumidor.java'], cwd=RAIZ, check=True)

    def rodar(self, *args, sucesso=True):
        r = subprocess.run(['java', '-cp', 'build', 'ProdutorConsumidor', *map(str, args)],
                           cwd=RAIZ, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0 if sucesso else 2, r.stdout + r.stderr)
        return r.stdout

    def conferir(self, p, c, t, n, *extras):
        saida = self.rodar('--produtores', p, '--consumidores', c, '--buffer', t,
                          '--itens', n, *extras)
        resumo = dict(x.split('=', 1) for x in saida.splitlines()[-1].split())
        for chave in ('itens', 'consumidos', 'unicos'):
            self.assertEqual(int(resumo[chave]), n)
        for chave in ('repetidos', 'invalidos', 'restantes'):
            self.assertEqual(int(resumo[chave]), 0)
        self.assertLessEqual(int(resumo['pico']), t)
        self.assertEqual(resumo['status'], 'OK')
        return saida

    def test_seis_cenarios(self):
        for p, c in [(10, 10), (10, 5), (5, 10)]:
            for t in (1, 20):
                with self.subTest(p=p, c=c, t=t):
                    self.conferir(p, c, t, 2000)

    def test_zero_itens_encerra(self):
        self.conferir(10, 10, 1, 0)

    def test_mais_threads_que_itens(self):
        self.conferir(10, 10, 20, 3)

    def test_produtor_mais_lento(self):
        self.conferir(1, 5, 1, 25, '--atraso-prod-ms', 1)

    def test_consumidor_mais_lento(self):
        self.conferir(5, 1, 1, 25, '--atraso-cons-ms', 1)

    def test_fifo_e_limites_no_log(self):
        # O log é escrito dentro do monitor, permitindo reconstruir a fila.
        saida = self.conferir(4, 3, 3, 150, '--log')
        fila = []
        for acao, item, ocupacao, capacidade in re.findall(
                r'(produziu|consumiu) (\d+) \| buffer=(\d+)/(\d+)', saida):
            if acao == 'produziu':
                fila.append(int(item))
            else:
                self.assertTrue(fila)
                self.assertEqual(fila.pop(0), int(item))
            self.assertEqual(len(fila), int(ocupacao))
            self.assertLessEqual(len(fila), int(capacidade))
        self.assertEqual(fila, [])
        self.assertEqual(len(re.findall(r'produziu \d+', saida)), 150)
        self.assertEqual(len(re.findall(r'consumiu \d+', saida)), 150)

    def test_configuracoes_invalidas(self):
        for args in [('--produtores', 0), ('--consumidores', -1), ('--buffer', 0),
                     ('--itens', -1), ('--itens', 'abc'), ('--buffer',),
                     ('--desconhecido', 1), ('--atraso-prod-ms', -1)]:
            with self.subTest(args=args):
                self.rodar(*args, sucesso=False)

    def test_encerramento_repetido(self):
        for _ in range(10):
            self.conferir(5, 10, 1, 30)


if __name__ == '__main__':
    unittest.main(verbosity=2)
