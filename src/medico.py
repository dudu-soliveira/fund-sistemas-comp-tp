import sys
from concurrent import futures
from threading import Condition, Lock, Semaphore
from typing import Any, Tuple

import grpc

import consultorio_pb2_grpc
from ambulatorio_pb2 import *
from ambulatorio_pb2_grpc import AmbulatorioServiceStub
from consultorio_pb2 import *
from mytimer import mysleep, tstamp_msg

tipo_porto = int
tipo_ident = float
tipo_ender = str
tipo_tempo = float

porta_aberta: Semaphore
consulta_completa: Semaphore
id_paciente: tipo_ident
problema: str
resultado: int


def init_vars() -> None:
    global porta_aberta, consulta_completa, id_paciente, problema, resultado
    porta_aberta = Semaphore(0)
    consulta_completa = Semaphore(0)
    id_paciente = 0
    problema = ""
    resultado = 0


class Ambulatorio:
    endereco: tipo_ender
    porta: tipo_porto

    def __init__(self, endereco: tipo_ender, porta: tipo_porto) -> None:
        self.endereco = endereco
        self.porta = porta

    def connect(self) -> grpc.Channel:
        return grpc.insecure_channel(f"{self.endereco}:{self.porta}")


class Medico:
    amb: Ambulatorio
    id: tipo_ident
    porta: tipo_porto

    def __init__(
        self,
        amb: Ambulatorio,
        id: tipo_ident,
        porta: tipo_porto,
    ) -> None:
        self.amb = amb
        self.id = id
        self.porta = porta

    def rotina(self) -> None:
        global porta_aberta, consulta_completa, resultado, id_paciente

        while True:
            with self.amb.connect() as channel:
                stub = AmbulatorioServiceStub(channel)
                tstamp_msg("AMB")

                req = ChamaPacienteRequest(id_medico=self.id)
                res = stub.ChamaPaciente(req)
                id_paciente = res.id_paciente

                tstamp_msg(f"AMB -> {id_paciente:4.1f}")

            if id_paciente < 1:
                exit()

            tstamp_msg(f"CP({id_paciente:4.1f})")
            porta_aberta.release()
            consulta_completa.acquire()
            tstamp_msg(f"CE -> {resultado}")

    def registraMedico(self) -> int:
        with self.amb.connect() as channel:
            stub = AmbulatorioServiceStub(channel)
            req = RegistraMedicoRequest(id_medico=self.id, porto=self.porta)
            res = stub.RegistraMedico(req)
            return res.resultado


class ConsultorioServicer(consultorio_pb2_grpc.ConsultorioServiceServicer):
    duracao: tipo_tempo

    def __init__(self, duracao: tipo_tempo) -> None:
        self.duracao = duracao

    def Consulta(self, request: ConsultaRequest, context) -> ConsultaResponse:
        global porta_aberta, consulta_completa, id_paciente, problema
        porta_aberta.acquire()

        id_paciente = request.id_paciente
        problema = request.problema
        tstamp_msg(f"CM({id_paciente:4.1f},{problema})")
        mysleep(self.duracao)
        resultado = 0

        consulta_completa.release()
        tstamp_msg(f"CM({id_paciente:4.1f}) -> {resultado}")
        return ConsultaResponse(resultado=resultado)


def parse_args() -> Tuple[tipo_porto, tipo_ident, tipo_tempo, tipo_ender, tipo_porto]:
    try:
        args = sys.argv
        if len(args) != 6:
            raise
        return (
            tipo_porto(args[1]),
            tipo_ident(args[2]),
            tipo_tempo(args[3]),
            args[4],
            tipo_porto(args[5]),
        )
    except:
        raise Exception(
            "Argumentos inválidos. Devem ser "
            + "[porta do consultório: int] [id do médico: float] [tempo de consulta: string] "
            + "[endereço do ambulatório: string] [porta do ambulatório: int]",
            sys.argv,
        )


def serve(duracao: tipo_tempo, porta: tipo_porto) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    consultorio_pb2_grpc.add_ConsultorioServiceServicer_to_server(
        ConsultorioServicer(duracao), server
    )
    server.add_insecure_port(f"[::]:{porta}")
    server.start()
    return server


def main() -> None:
    (porta, id, duracao, endereco_amb, porta_amb) = parse_args()
    tstamp_msg(f"SC({id:4.1f}) x {duracao:3.1f} @ {porta}")
    init_vars()
    amb = Ambulatorio(endereco_amb, porta_amb)
    medico = Medico(amb, id, porta)

    server = serve(duracao, porta)
    resultado = medico.registraMedico()
    if resultado == -1:
        server.stop(1)
        exit()

    medico.rotina()


if __name__ == "__main__":
    main()
