#!/usr/bin/env python3
"""Gera somente o pacote desta entrega. Bruno Barros e Luana Barros."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

raiz = Path(__file__).resolve().parent.parent
arquivo = raiz / 'entrega_produtor_consumidor.zip'
fixos = ['README.md', 'FONTES.md', 'RELATORIO.md', 'executar.sh']
pastas = ['src', 'scripts', 'testes', 'resultados']
with ZipFile(arquivo, 'w', compression=ZIP_DEFLATED) as pacote:
    for nome in fixos:
        pacote.write(raiz / nome, f'produtor-consumidor/{nome}')
    for pasta in pastas:
        for caminho in sorted((raiz / pasta).rglob('*')):
            if caminho.is_file() and '__pycache__' not in caminho.parts:
                pacote.write(caminho, 'produtor-consumidor/' + caminho.relative_to(raiz).as_posix())
print(arquivo)
