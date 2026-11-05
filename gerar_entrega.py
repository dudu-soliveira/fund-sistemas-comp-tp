#!/usr/bin/env python3
"""Gera o ZIP com os sete arquivos exigidos no enunciado e o relatório PDF."""

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

src = Path(__file__).resolve().parent / "src"
relatorio = src.parent / "relatorio.pdf"
destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("entrega.zip")
arquivos = {
    "ambulatorio.proto": "ambulatorio.proto",
    "consultorio.proto": "consultorio.proto",
    "paciente.py": "paciente.py",
    "medico.py": "medico.py",
    "ambulatorio.py": "ambulatorio.py",
    "fim_do_expediente.py": "fim_do_expediente.py",
}

if len(sys.argv) > 2:
    sys.exit(f"Uso: {sys.argv[0]} [arquivo.zip]")

faltando = [nome for nome in arquivos if not (src / nome).is_file()]
if not (src / "Makefile").is_file():
    faltando.append("Makefile")
if faltando:
    sys.exit(f"Arquivos ausentes em {src}: {', '.join(faltando)}")
if not relatorio.is_file():
    sys.exit(f"Relatório ausente: {relatorio}")

# Retira apenas os alvos e a opção gerados pelo plugin mypy-protobuf.
makefile = (src / "Makefile").read_text()
substituicoes = {
    "stubs: ambulatorio_pb2_grpc.py consultorio_pb2_grpc.py \\\n\t\tambulatorio_pb2_grpc.pyi consultorio_pb2_grpc.pyi": "stubs: ambulatorio_pb2_grpc.py consultorio_pb2_grpc.py",
    "%_pb2.py %_pb2.pyi %_pb2_grpc.py %_pb2_grpc.pyi &: %.proto": "%_pb2.py %_pb2.pyi %_pb2_grpc.py &: %.proto",
    "\t\t--mypy_grpc_out=. \\\n": "",
}
for original, substituto in substituicoes.items():
    if makefile.count(original) != 1:
        sys.exit("Não foi possível adaptar o Makefile local para a entrega.")
    makefile = makefile.replace(original, substituto)

with ZipFile(destino, "w", compression=ZIP_DEFLATED) as zip_file:
    for origem, nome_no_zip in arquivos.items():
        zip_file.write(src / origem, nome_no_zip)
    zip_file.writestr("Makefile", makefile)
    zip_file.write(relatorio, "relatorio.pdf")

print(f"Entrega gerada: {destino}")
