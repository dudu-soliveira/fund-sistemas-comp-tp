import sys
from typing import Tuple

import grpc

from ambulatorio_pb2 import *
from ambulatorio_pb2_grpc import AmbulatorioServiceStub
from mytimer import tstamp_msg

tipo_porto = int
tipo_ident = float
tipo_ender = str
tipo_tempo = float


def parse_args() -> Tuple[tipo_ender, tipo_porto]:
    try:
        args = sys.argv
        if len(args) != 3:
            raise
        return (args[1], tipo_porto(args[2]))
    except:
        raise Exception(
            "Argumentos inválidos. Devem ser "
            + "[endereço do ambulatório: string] [porta do ambulatório: int]",
            sys.argv,
        )


class Server:
    endereco: tipo_ender
    porta: tipo_porto

    def __init__(self, endereco: tipo_ender, porta: tipo_porto):
        self.endereco = endereco
        self.porta = porta

    def connect(self) -> int:
        with grpc.insecure_channel(f"{self.endereco}:{self.porta}") as channel:
            stub = AmbulatorioServiceStub(channel)
            req = TerminoRequest()
            res = stub.Termino(req)
            return res.num_liberados


def main() -> None:
    (endereco, porta) = parse_args()
    tstamp_msg("FE(%s,%d)" % (endereco, porta))

    ambulatorio = Server(endereco, porta)

    num_liberados = ambulatorio.connect()
    tstamp_msg("FE -> %d" % num_liberados)


if __name__ == "__main__":
    main()
