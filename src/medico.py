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
paciente_chegou: Semaphore
consulta_completa: Semaphore
id_paciente: tipo_ident
problema: str


def init_vars() -> None:
    global porta_aberta, paciente_chegou, consulta_completa, id_paciente, problema
    porta_aberta = Semaphore(0)
    paciente_chegou = Semaphore(0)
    consulta_completa = Semaphore(0)
    id_paciente = 0
    problema = ""


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
        global porta_aberta, paciente_chegou, consulta_completa, id_paciente

        while True:
            with self.amb.connect() as channel:
                stub = AmbulatorioServiceStub(channel)
                tstamp_msg("MCPI")

                req = ChamaPacienteRequest(id_medico=self.id)
                res = stub.ChamaPaciente(req)
                id_paciente = res.id_paciente

                tstamp_msg("MCPR -> %4.1f" % id_paciente)

            if id_paciente < 1:
                tstamp_msg("MT ")
                exit()

            # Abre a porta e espera o paciente chegar
            porta_aberta.release()
            paciente_chegou.acquire()
            tstamp_msg("MAI(%4.1f)" % id_paciente)

            # Apos o paciente chegar, espera o fim da consulta
            consulta_completa.acquire()
            tstamp_msg("MAF -> %d" % self.id)

    def registraMedico(self) -> int:
        with self.amb.connect() as channel:
            stub = AmbulatorioServiceStub(channel)
            req = RegistraMedicoRequest(id_medico=self.id, porto=self.porta)
            res = stub.RegistraMedico(req)
            return res.resultado


class ConsultorioServicer(consultorio_pb2_grpc.ConsultorioServiceServicer):
    id: tipo_ident
    duracao: tipo_tempo

    def __init__(self, id: tipo_ident, duracao: tipo_tempo) -> None:
        self.id = id
        self.duracao = duracao

    def Consulta(self, request: ConsultaRequest, context) -> ConsultaResponse:
        global porta_aberta, paciente_chegou, consulta_completa, id_paciente, problema

        tstamp_msg("CI(%4.1f,%s)" % (request.id_paciente, request.problema))

        # Espera a porta ser aberta
        porta_aberta.acquire()

        # Preenche os dados do paciente e sinaliza sua chegada
        id_paciente = request.id_paciente
        problema = request.problema
        paciente_chegou.release()

        mysleep(self.duracao)

        tstamp_msg("CR(%4.1f,%4.1f) -> %d" % (id_paciente, self.id, self.id))
        consulta_completa.release()
        return ConsultaResponse(id_medico=self.id)


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


def serve(id: tipo_ident, duracao: tipo_tempo, porta: tipo_porto) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    consultorio_pb2_grpc.add_ConsultorioServiceServicer_to_server(
        ConsultorioServicer(id, duracao), server
    )
    server.add_insecure_port(f"[::]:{porta}")
    server.start()
    return server


def main() -> None:
    (porta, id, duracao, endereco_amb, porta_amb) = parse_args()
    tstamp_msg("MI(%4.1f) x %3.1f @ %d" % (id, duracao, porta))
    init_vars()
    amb = Ambulatorio(endereco_amb, porta_amb)
    medico = Medico(amb, id, porta)

    server = serve(id, duracao, porta)
    resultado = medico.registraMedico()
    if resultado == -1:
        server.stop(1)
        exit()

    medico.rotina()


if __name__ == "__main__":
    main()
