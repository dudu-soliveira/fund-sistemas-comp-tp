import sys
from concurrent import futures
from threading import Condition, Event, Lock
from typing import Dict, List, Optional, Tuple, cast

import grpc

import ambulatorio_pb2_grpc
from ambulatorio_pb2 import *
from mytimer import mysleep, tstamp_msg

tipo_porto = int
tipo_ident = float
tipo_ender = str


def split_peer(addr_str: str) -> Tuple[tipo_ender, tipo_porto]:
    # Remove gRPC's transport prefix, if present.
    if addr_str.startswith(("ipv4:", "ipv6:")):
        addr_str = addr_str.split(":", 1)[1]

    address, _, port = addr_str.rpartition(":")
    # Remove brackets around an IPv6 address.
    if address.startswith("[") and address.endswith("]"):
        address = address[1:-1]

    return address, tipo_porto(port)


class Consultorio:
    porto: tipo_porto
    endereco: tipo_ender

    def __init__(self, porto: tipo_porto, endereco: tipo_ender):
        self.porto = porto
        self.endereco = endereco


class RegistrosMedicos:
    mutex: Lock
    total: int
    mp: Dict[float, Consultorio]

    def __init__(self, total: int):
        self.mutex = Lock()
        self.total = total
        self.count = 0
        self.mp = dict()

    def set(self, id: tipo_ident, porto: tipo_porto, endereco: tipo_ender) -> int:
        # Precisamos sincronizar para impedir que multiplos medicos sejam adicionados
        # simultaneamente quando ja se tem (total - 1) medicos
        with self.mutex:
            if self.full() or self.mp.get(id) is not None:
                return -1

            self.mp[id] = Consultorio(porto, endereco)
            self.count += 1
            return 0

    def get(self, id: tipo_ident) -> Consultorio:
        return self.mp.get(id, Consultorio(0, ""))

    def full(self) -> bool:
        return self.count == self.total


class Prontuario:
    cond: Condition
    id_medico: Optional[tipo_ident]
    id_paciente: Optional[tipo_ident]

    def __init__(
        self,
        mutex: Optional[Lock] = None,
        id_medico: Optional[tipo_ident] = None,
        id_paciente: Optional[tipo_ident] = None,
    ):
        self.cond = Condition(mutex)
        self.id_medico = id_medico
        self.id_paciente = id_paciente


class Fila:
    total: int
    fila: List[Prontuario]
    count: int
    inicio: int
    fim: int

    def __init__(self, total: int):
        self.total = total
        self.fila = [Prontuario() for _ in range(total)]
        self.count = 0
        self.inicio = 0
        self.fim = -1

    def pop(self) -> Prontuario:
        # Retorna um prontuario vazio se a fila estiver vazia (na pratica esse caso nunca ocorre)
        if self.empty():
            return Prontuario()

        # Caso contrario, remove o primeiro e atualiza o ponteiro usando o modulo para nao ultrapassar o fim da lista
        primeiro = self.fila[self.inicio]
        self.inicio = (self.inicio + 1) % self.total
        self.count -= 1
        return primeiro

    def push(self, no: Prontuario) -> bool:
        # Retorna falso quando a lista ja esta cheia
        if self.full():
            return False

        # Caso contrario, atualiza o ponteiro do fim de maneira circular e adiciona o novo prontuario na fila
        self.fim = (self.fim + 1) % self.total
        self.fila[self.fim] = no
        self.count += 1
        return True

    def empty(self) -> bool:
        return self.count == 0

    def full(self) -> bool:
        return self.count == self.total


class AmbulatorioServicer(ambulatorio_pb2_grpc.AmbulatorioServiceServicer):
    pacientes: Fila
    medicos: Fila
    registros_medicos: RegistrosMedicos
    chamadas: int
    parada: Event
    mutex: Lock
    cond: Condition
    block: bool

    def __init__(self, total_pacientes: int, total_medicos: int, parada: Event):
        self.pacientes = Fila(total_pacientes)
        self.medicos = Fila(total_medicos)
        self.registros_medicos = RegistrosMedicos(total_medicos)
        self.chamadas = 0
        self.parada = parada
        self.mutex = Lock()
        self.cond = Condition(self.mutex)
        self.block = False

    def ProcuraMedico(
        self, request: ProcuraMedicoRequest, context
    ) -> ProcuraMedicoResponse:
        with self.mutex:
            # Impedir que novas requisicoes sejam computadas durante o processo de termino
            if self.block:
                return ProcuraMedicoResponse(endereco="", porto=0)
            self.chamadas += 1

            id_paciente = request.id_paciente
            tstamp_msg("APMI(%4.1f)" % id_paciente)

            # Se a fila de pacientes estiver cheia, retorna um endereco vazio
            if self.pacientes.full():
                self.chamadas -= 1
                self.cond.notify()
                return ProcuraMedicoResponse(endereco="", porto=0)

            # Se existir pelo menos um medico esperando, preenchemos o prontuario
            # do primeiro da fila com os dados do paciente e o notificamos
            if not self.medicos.empty():
                prontuario = self.medicos.pop()
                prontuario.id_paciente = id_paciente
                prontuario.cond.notify()

                id_medico = cast(tipo_ident, prontuario.id_medico)

            # Caso contrario, criamos um novo prontuario com os dados do paciente, o adicionamos
            # na fila e esperamos ate que um medico preencha seus dados no prontuario
            else:
                prontuario = Prontuario(self.mutex, None, id_paciente)
                self.pacientes.push(prontuario)

                tstamp_msg("APME(%4.1f) ESPERA" % id_paciente)
                while prontuario.id_medico is None:
                    prontuario.cond.wait()

                id_medico = prontuario.id_medico

            medico = self.registros_medicos.get(id_medico)
            endereco = medico.endereco
            porto = medico.porto

            tstamp_msg(
                "APMR(%4.1f) -> M(%4.1f) @ %s:%d"
                % (id_paciente, id_medico, endereco, porto)
            )
            self.chamadas -= 1
            self.cond.notify()
            return ProcuraMedicoResponse(endereco=endereco, porto=porto)

    def RegistraMedico(
        self, request: RegistraMedicoRequest, context
    ) -> RegistraMedicoResponse:
        with self.mutex:
            # Impedir que novas requisicoes sejam computadas durante o processo de termino
            if self.block:
                return RegistraMedicoResponse(resultado=-1)
            self.chamadas += 1

            id_medico = request.id_medico
            porto = request.porto
            endereco = split_peer(context.peer())[0]

            res = self.registros_medicos.set(id_medico, porto, endereco)

            tstamp_msg("ARM(%4.1f) @ %s:%d = %d" % (id_medico, endereco, porto, res))
            self.chamadas -= 1
            self.cond.notify()
        return RegistraMedicoResponse(resultado=res)

    def ChamaPaciente(
        self, request: ChamaPacienteRequest, context
    ) -> ChamaPacienteResponse:
        with self.mutex:
            # Impedir que novas requisicoes sejam computadas durante o processo de termino
            if self.block:
                return ChamaPacienteResponse(id_paciente=0)
            self.chamadas += 1

            id_medico = request.id_medico
            tstamp_msg("ACPI(%4.1f)" % id_medico)

            # Se existir ao menos um paciente esperando, removemos o prontuario do primeiro e preenchemos os
            # dados do medico nele, notificamos o paciente e retornamos os seus dados ao medico
            if not self.pacientes.empty():
                prontuario = self.pacientes.pop()
                prontuario.id_medico = id_medico
                prontuario.cond.notify()

                id_paciente = cast(tipo_ident, prontuario.id_paciente)

            # Caso contrario, criamos um novo prontuario com os dados do medico
            # e esperamos ate que um paciente seja atrelado a esse prontuario
            else:
                prontuario = Prontuario(self.mutex, id_medico, None)
                self.medicos.push(prontuario)

                tstamp_msg("ACPE(%4.1f)" % id_medico)
                while prontuario.id_paciente is None:
                    prontuario.cond.wait()

                id_paciente = prontuario.id_paciente

            tstamp_msg("ACPR(%4.1f) -> P(%4.1f)" % (id_medico, id_paciente))
            self.chamadas -= 1
            self.cond.notify()
            return ChamaPacienteResponse(id_paciente=id_paciente)

    def Termino(self, request: TerminoRequest, context) -> TerminoResponse:
        with self.mutex:
            tstamp_msg("ATEI")
            self.block = True

            liberados = 0

            while not self.medicos.empty():
                prontuario = self.medicos.pop()
                prontuario.id_paciente = 0
                prontuario.cond.notify()
                liberados += 1

            while not self.pacientes.empty():
                prontuario = self.pacientes.pop()
                prontuario.id_medico = 0
                prontuario.cond.notify()
                liberados -= 1

            while self.chamadas > 0:
                self.cond.wait()

            mysleep(1)
            self.parada.set()

            tstamp_msg("ATER -> %d" % liberados)
            return TerminoResponse(num_liberados=liberados)


def parse_args() -> Tuple[int, int, tipo_porto]:
    try:
        args = sys.argv
        if len(args) != 4:
            raise
        return (int(args[1]), int(args[2]), tipo_porto(args[3]))
    except:
        raise Exception(
            "Argumentos inválidos. Devem ser "
            + "[número de cadeiras: int] [número de médicos: int] [número da porta: int]",
            sys.argv,
        )


def serve(total_pacientes: int, total_medicos: int, porto: tipo_porto) -> None:
    parada = Event()
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max(total_pacientes, total_medicos) + 1)
    )
    ambulatorio_pb2_grpc.add_AmbulatorioServiceServicer_to_server(
        AmbulatorioServicer(total_pacientes, total_medicos, parada), server
    )
    server.add_insecure_port(f"[::]:{porto}")
    server.start()

    parada.wait()
    server.stop(1)


def main() -> None:
    (total_pacientes, total_medicos, porto) = parse_args()
    tstamp_msg("AI(%d,%d)@%d" % (total_pacientes, total_medicos, porto))
    serve(total_pacientes, total_medicos, porto)


if __name__ == "__main__":
    main()
