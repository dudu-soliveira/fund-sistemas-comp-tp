#!/usr/bin/env python3
"""Gera o ZIP de entrega com os sete arquivos exigidos no enunciado."""

from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile


src = Path(__file__).resolve().parent / "src"
destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("entrega.zip")
arquivos = {
    "ambulatorio.proto": "ambulatorio.proto",
    "consultorio.proto": "consultorio.proto",
    "paciente.py": "paciente.py",
    "medico.py": "medico.py",
    "ambulatorio.py": "ambulatorio.py",
    "fim_do_expediente.py": "fim_de_expediente.py",
}

if len(sys.argv) > 2:
    sys.exit(f"Uso: {sys.argv[0]} [arquivo.zip]")

faltando = [nome for nome in arquivos if not (src / nome).is_file()]
if faltando:
    sys.exit(f"Arquivos ausentes em {src}: {', '.join(faltando)}")

with ZipFile(destino, "w", compression=ZIP_DEFLATED) as zip_file:
    for origem, nome_no_zip in arquivos.items():
        zip_file.write(src / origem, nome_no_zip)
    # O Makefile de entrega não exige o plugin de tipagem usado localmente.
    zip_file.writestr("Makefile", """.PHONY: stubs clean

stubs:
	python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ambulatorio.proto consultorio.proto

clean:
	rm -f *_pb2.py *_pb2_grpc.py *_pb2.pyi *_pb2_grpc.pyi
""")

print(f"Entrega gerada: {destino}")
