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


class Shared:
    porta_aberta: Semaphore
    paciente_chegou: Semaphore
    paciente_registrado: Semaphore
    consulta_completa: Semaphore
    id_paciente: tipo_ident
    problema: str

    def __init__(self):
        self.porta_aberta = Semaphore(0)
        self.paciente_chegou = Semaphore(0)
        self.paciente_registrado = Semaphore(0)
        self.consulta_completa = Semaphore(0)
        self.id_paciente = 0
        self.problema = ""


shared: Shared


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
    duracao: tipo_tempo

    def __init__(
        self, amb: Ambulatorio, id: tipo_ident, porta: tipo_porto, duracao: tipo_tempo
    ) -> None:
        self.amb = amb
        self.id = id
        self.porta = porta
        self.duracao = duracao

    def rotina(self) -> None:
        global shared

        while True:
            # Faz a chamada de um paciente no ambulatorio
            with self.amb.connect() as channel:
                stub = AmbulatorioServiceStub(channel)
                tstamp_msg("MCPI")

                req = ChamaPacienteRequest(id_medico=self.id)

                # O servidor pode fechar enquanto o medico esta dormindo, quando esse for
                # o caso, um erro sera lancado ao tentar conectar-se ao ambulatorio
                try:
                    res = stub.ChamaPaciente(req)
                    id_paciente = res.id_paciente
                    tstamp_msg("MCPR -> %4.1f" % id_paciente)
                except grpc.RpcError:
                    tstamp_msg("MT ")
                    exit()

            # Se o paciente for invalido, finaliza a execucao
            if id_paciente < 1:
                tstamp_msg("MT ")
                exit()

            # Espera o paciente chegar e abre a porta
            shared.paciente_chegou.acquire()
            shared.porta_aberta.release()

            # Espera o paciente ser registrado e comeca a consulta
            shared.paciente_registrado.acquire()
            tstamp_msg("MAI(%4.1f,%s)" % (shared.id_paciente, shared.problema))
            mysleep(self.duracao)

            # Libera o paciente no fim da consulta
            shared.consulta_completa.release()
            tstamp_msg("MAF")

    def registraMedico(self) -> int:
        # Conecta-se ao ambulatorio e se registra
        with self.amb.connect() as channel:
            stub = AmbulatorioServiceStub(channel)
            req = RegistraMedicoRequest(id_medico=self.id, porto=self.porta)
            res = stub.RegistraMedico(req)
            return res.resultado


class ConsultorioServicer(consultorio_pb2_grpc.ConsultorioServiceServicer):
    id: tipo_ident

    def __init__(self, id: tipo_ident) -> None:
        self.id = id

    def Consulta(self, request: ConsultaRequest, context) -> ConsultaResponse:
        global shared

        # Sinaliza a chegada do paciente e espera a porta ser aberta
        shared.paciente_chegou.release()
        tstamp_msg("CI(%4.1f,%s)" % (request.id_paciente, request.problema))
        shared.porta_aberta.acquire()

        # Sinaliza o registro do cliente
        shared.id_paciente = request.id_paciente
        shared.problema = request.problema
        shared.paciente_registrado.release()

        # Espera o fim da consulta
        shared.consulta_completa.acquire()
        tstamp_msg("CR(%4.1f,%4.1f)" % (shared.id_paciente, self.id))
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


def serve(id: tipo_ident, porta: tipo_porto) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    consultorio_pb2_grpc.add_ConsultorioServiceServicer_to_server(
        ConsultorioServicer(id), server
    )
    server.add_insecure_port(f"[::]:{porta}")
    server.start()
    return server


def main() -> None:
    global shared

    # Inicializa as variaveis necessarias
    (porta, id, duracao, endereco_amb, porta_amb) = parse_args()
    shared = Shared()
    amb = Ambulatorio(endereco_amb, porta_amb)
    medico = Medico(amb, id, porta, duracao)

    # Inicia o servidor e registra o medico no ambulatorio
    server = serve(id, porta)
    resultado = medico.registraMedico()
    tstamp_msg("MI(%4.1f) x %3.1f @ %d = %d" % (id, duracao, porta, resultado))

    # Se o registro no ambulatorio falhar, para a execucao do medico e do servidor
    if resultado == -1:
        server.stop(1)
        exit()

    # Executa o loop do medico
    medico.rotina()


if __name__ == "__main__":
    main()
