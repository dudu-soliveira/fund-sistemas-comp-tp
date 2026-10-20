import sys
from typing import Tuple

import grpc

import ambulatorio_pb2_grpc
import consultorio_pb2_grpc
from ambulatorio_pb2 import *
from consultorio_pb2 import *
from mytimer import tstamp_msg

tipo_porto = int
tipo_ident = float
tipo_ender = str
tipo_tempo = float


def parse_args() -> Tuple[tipo_ident, str, tipo_ender, tipo_porto]:
    try:
        args = sys.argv
        if len(args) != 5:
            raise
        return (tipo_ident(args[1]), args[2], args[3], tipo_porto(args[4]))
    except:
        raise Exception(
            "Argumentos inválidos. Devem ser "
            + "[id do paciente: float] [descrição do problema: string] "
            + "[endereço do ambulatório: string] [porta do ambulatório: int]",
            sys.argv,
        )


class Server:
    endereco: tipo_ender
    porta: tipo_porto

    def __init__(self, endereco: tipo_ender, porta: tipo_porto):
        self.endereco = endereco
        self.porta = porta

    def connect(self) -> grpc.Channel:
        return grpc.insecure_channel(f"{self.endereco}:{self.porta}")


class Paciente:
    id: tipo_ident
    problema: str
    ambulatorio: Server
    consultorio: Server

    def __init__(self, id: tipo_ident, problema: str, ambulatorio: Server):
        self.id = id
        self.problema = problema
        self.ambulatorio = ambulatorio

    def procuraMedico(self) -> bool:
        with self.ambulatorio.connect() as channel:
            stub = ambulatorio_pb2_grpc.AmbulatorioServiceStub(channel)

            req = ProcuraMedicoRequest(id_paciente=self.id)
            res = stub.ProcuraMedico(req)
            end_consultorio = res.ip_consultorio
            porta_consultorio = res.porto
            tstamp_msg(f"CM({end_consultorio},{porta_consultorio})")

            if porta_consultorio == 0:
                return False

            self.consultorio = Server(end_consultorio, porta_consultorio)
            return True

    def consulta(self) -> None:
        with self.consultorio.connect() as channel:
            stub = consultorio_pb2_grpc.ConsultorioServiceStub(channel)

            req = ConsultaRequest(id_paciente=self.id, problema=self.problema)
            res = stub.Consulta(req)
            resultado = res.resultado
            tstamp_msg(f"CT -> {resultado}")


def main() -> None:
    (id, problema, end_amb, porta_amb) = parse_args()
    tstamp_msg(f"P({id:4.1f},{problema})")

    ambulatorio = Server(end_amb, porta_amb)
    paciente = Paciente(id, problema, ambulatorio)

    if not paciente.procuraMedico():
        return

    paciente.consulta()


if __name__ == "__main__":
    main()
