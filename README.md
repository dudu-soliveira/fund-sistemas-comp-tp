Trabalho individual ou em dupla
Data de entrega: confira na programação da disciplina.

    Alterações em relação à primeira versão em azul.
    Alteração em relação à segunda versão em laranja. (O formato de todas as mensagens foram alteradas)

Introdução

Neste exercício vamos praticar o desenvolvimento de aplicações baseadas em chamadas de procedimento remotos (RPC) que usam sincronização das threads internas com variáveis de exclusão mútua e condições ou semáforos. Na área de desenvolvimento de aplicações em nuvem, RPCs são provavelmente a técnica mais utilizada hoje para comunicação entre partes de um serviço em rede. Como discutido em sala, internamente, um servidor de RPC pode usar threads para atender cada RPC, gerando paralelismo interno e exigindo sincronização para controlar acesso a áreas compartilhadas (seções críticas). Muitas vezes, diversos serviços baseados em RPC são interligados entre si formando serviços mais complexos, como no caso do que se costuma chamar de arquiteturas de microsserviços. Neste exercício vamos exercitar esses conceitos em um mini-sistema.

Entre os frameworks de programação com RPC existem diversas opções. Neste exercício usaremos gRPC, por ser das opções populares que não estão presas a ambiente de desenvolvimento específicos (como Flask ou node.js, por exemplo).
Objetivo

Neste exercício você deve desenvolver, usando gRPC, um serviço simples de que simula um sistema de um pronto atendiento, por exemplo, onde podem haver vários médicos atendendo os pacientes na ordem de chegada. A implementação pode ser dividida em dois servidores: o serviço de controle do ambulatório e o serviço de atendimento pelo médico propriamente dito.
Tipos pré-definidos

Os seguintes tipos usados nesta descrição deverão ser usados também na implementação:

    tipo_porto: inteiro positivo de dois bytes;
    tipo_ident: número de ponto flutuante de precisão simples (float), será maior que 1 em identificadores válidos;
    tipo_ender: string com um nome de máquina ou endereço IP;
    tipo_tempo: número de ponto flutuante de precisão simples (float) que representa um intervalo em segundos;
    tipo_prontuário: um registro com os identificadores do paciente e do médico (tipo_ident).

Formato da saída

Os programas descritos a seguir devem produzir apenas as saídas indicadas. Nenhuma mensagem além das mencionadas a seguir deve ser escrita, sob pena de inviabilizar a correção automática (o que será penalizado).
O servidor de ambulatório

O ponto central do seu trabalho será implementar um servidor de RPC que simula algumas das tarefas de um ambulatório médido de pronto atendimento. Nesse ambiente, pacientes que chegam e não encontram médicos imediatamente disponíveis devem esperar em uma fila, sentados na ante-sala. Se a ante-sala estiver cheia (nenhuma cadeira disponível), o paciente vai preferir ir embora e voltar mais tarde - vamos assumir que ninguém chega com uma condição grave!

Seu servidor de ambulatório deve exportar o seguintes procedimentos:

    procura por um médico: chamado por um processo de um paciente, recebe como parâmetro um número de ponto flutuante (tipo_ident) contendo o identificador do paciente; retorna um string com o nome/endereço IP de uma máquina e um inteiro com o número da porta onde ele encontrará o servidor do consultório do médico;
    registra médico: executado por um médico ao começar, antes de poder chamar pacientes. Recebe  o identificador do médico (tipo_ident) e um número (tipo_porto); (deve obter o endereço do servidor da API do grpc, como mencionado mais tarde;) retorna 0 se o registro foi bem sucedido e -1 caso contrário;
    chama um paciente: executado por um médico quando estiver pronto para atender um novo paciente, recebe como parâmetros o identificador do médico (tipo_ident) e retorna o número de ponto flutuante com o identificador do próximo paciente;
    término: um procedimento sem parâmetros que indica que o servidor deve liberar os médicos que estejam esperando por pacientes (ou pacientes esperando por médicos, infelizmente) e termina sua execução; retorna o número de médicos ou pacientes que foram liberados, sendo que se foram liberados pacientes o valor deve ser negativo para permitir a distinção entre os dois casos.

O servidor do ambulatório será iniciado com três argumentos de linha de comando: o primeiro indica o número de cadeiras na sala de espera do ambulatório, o segundo indica o número de médicos trabalhando e o terceiro, o número da porta que deverá ser usada pelo processo servidor. O servidor termina depois que o procedimento término tiver sido completado (mais sobre como fazer isso ao final).

O servidor do ambulatório deve manter internamente duas filas de prontuários (semântica FIFO), uma para os pacientes que esperam e outra para os médicos que estejam livres em um certo momento. O tamanho das filas será definido pelos argumentos de linha de comando. Essas filas serão manipuladas pelas threads que executarão os procedimentos remotos e devem portanto seguir regras de sincronização, definidas a seguir.
Regras de sincronização do ambulatório

A manipulação de prontuários das filas de pacientes e médicos deve ser feita com exclusão mútua. A ideia é que no ambulatório é feito um pareamento entre paciente e médico. Aquele que chega primeiro começa a preencher um prontuário com a sua parte das informações e espera pela chegada da outra parte. Quando a outra parte chega, os dois podem prosseguir para a realização da consulta propriamente dita, no consultório (os procedimentos do servidor de ambulatório retornam para os processos que representam o médico e o paciente. Prontuários incompletos (um cliente que espera por um médico ou vice-e-versa) implicam que uma thread está esperando pelo outro elemento do par (médico ou paciente). Para isso, a definição de cada prontuário deve incluir uma variável de condição onde a thread que espera aguardará pela notificação da segunda parte.

No procedimento procura por um médico, se fila de espera estiver cheia, o procedimento retorna imediatamente com um identificador de médico igual a zero, um string tipo_ender vazio e um inteiro tipo_porto igual a zero. Caso contrário, se houver um médico disponível, o método deve remover o prontuário da fila de médicos, preencher o campo com o identificador do paciente, sinalizar para que o médico que criou o prontuário possa prosseguir e retornar com o endereço do servidor e da que idenficam o consultório. Por outro lado, se não houver um médico disponível, o paciente deve criar um prontuário, preencher seu identifidador, inseri-lo na fila de pacientes e aguardar a notificação de que ele prosseguir. Quando isso acontecer, o método deve retornar com o identificador do servidor e a porta do consultório do médico. Essa informação poderá ser obtida no ambulatório, com base no identificador do médico que terá sido preenchido no prontuário.

O procedimento registra médico serve para registrar as informações sobre o médico que serão necessárias: seu identificador e o número da porta onde se encontra o seu consultório. Se o número de médicos definido na execução já tiver sido alcançado, a função retorna imediatamente com -1. Caso contrário, as informações fornecidas, junto com o endereço do servidor onde o médico se encontra, devem ser armazenados em um diretório dos médicos, indexados pelo identificador do médico e retorna 0. 

No procedimento chamada de um paciente, se houver algum prontuário na fila de pacientes, o médico remove o primeiro prontuário da fila, preenche o seu identifiador nele, notifica o paciente que aguarda o prontuário ser completado e retorna com o identificador do paciente. Caso não haja pacientes esperando na fila, ele cria um prontuário com a sua identificação, coloca-o na fila de médicos e vai esperar pela notificação de que pode prosseguir, quando ela retorna com o identificador do paciente obtido do prontuário. Exceto no final do expediente, quando ele estiver pronto para retornar ele deve demorar 0,1 segundo antes de fazê-lo (vai beber uma água usando um sleep antes de começar a próximar consulta ).

No procedimento término do expediente, se há médicos esperando por pacientes, seus prontuários devem ser preenchidos com valor zero no campo do identificador do paciente e eles devem ser notificados para que possam retornar. Se há pacientes esperando, seus prontuários devem ser preenchidos com zero on identificador do médico e eles devem ser notificados para que possam prosseguir. Só depois que todos os pacientes/médicos tenham retornado (nenhum outro procedimento esteja ainda em execução) o processo pode retornar com o número de médicos/pacientes que foram notificados e o servidor pode realmente terminar. Isto é, o próprio procedimento não pode causar a terminação do processo, caso contrário não seria possível retornar um valor. Para isso é preciso usar uma solução específica para terminar o servidor depois do retorno do procedimento, o que será explicado mais à frente. 
Mensagens escritas no ambulatório

    início da execução: 
        "AI(%d,%d)@%d" % (número de cadeiras, número de medicos, porto usado pelo servidor)
    procura por um médico:
        "APMI(%4.1f)" % (identificação do paciente) - ao iniciar
        "APME(%4.1f)" % (identificação do paciente) - imediatamente antes de parar para aguardar a notificação de um médico
        "APMR(%4.1f) -> M(%4.1f) @ %s:%d" % (identificação do paciente, identificação do médico, endereço do servidor de consultório, porta) - imediatamente antes de retornar
    registra médico:
        "ARM(%4.1f) @ %s:%d = %d" % (identificação do médico, endereço do servidor de consultório, porta, valor de retorno) - antes de retornar
    chamada de um paciente: 
        "ACPI(%4.1f)" % (identificação do médico) - ao iniciar
        "ACPE(%4.1f)" % (identificação do médico) - imediatamente antes de parar para aguardar a chegada de um paciente
        "ACPR(%4.1f) -> P(%4.1f)" % (identificação do médico, identificação do paciente) - imediatamente antes de retornar
    término do expediente:
        "ATEI"  - ao iniciar
        "ATER -> %d" % (valor de retorno) - imediatamente antes de retornar

O servidor de consultório (o médico)

O servidor de consultório será um processo que implementa o próprio médico. A parte do servidor executará em um porto passado como parâmetro e deve exportar apenas um procedimento:

    consulta: recebe como parâmetros o identificador do paciente (tipo_ident) e um string com a descrição do problema do paciente. Deve esperar o processo do médico abrir a porta do consultório, se identificar e informar o problema que o levou ao ambulatório. Deve depois esperar até que o médico termine a consulta, retornando com o valor do identificador do médico.

Funcionamento do processo do médico

O processo do médico será iniciado com cinco argumentos de linha de comando: o número da porta (tipo_porto) onde o servidor do consultório executará, um identificador do médico (tipo_ident), o tempo que ele gasta em cada consulta (tipo_tempo), o endereço (tipo_ender) e o número da porta (tipo_porto) onde ele encontrará o ambulatório. 

O médico deve inicialmente disparar o servidor do consultório na porta fornecida como argumento e se registrar no ambulatório informando seu identificador e o número da porta do consultório. o processo deve terminar sua execução 

Depois disso ele deve executar sua rotina diária, que implica em fazer a chamada de um paciente no ambulatório, esperar que o paciente execute o método consulta no servidor local, abrir a sala para o paciente, receber dele o seu identificador e a descrição do problema do paciente, escrever na sua saída padrão essas duas informações, executar um sleep pelo tempo da consulta e liberar o cliente depois disso, retornando ao ambulatório para chamar outro paciente.

Esse comportamento implica em dois pontos de sincronização entre a thread do servidor de consultório (que executa o RPC consulta) e a thread principal (que executa o laço do médico):

    Ao receber uma chamada de consulta, a thread do servidor deve esperar até que a thread principal sinalize que está pronta para atender — isto é, que o médico “abriu a porta”. Só então a thread do médico pode registrar os dados do paciente e prosseguir com a consulta.
    A thread principal (o médico), após sinalizar que está pronta, deve esperar até que a consulta termine com o sleep — só depois disso o médico pode liberar o paciente e voltar ao ambulatório para chamar o próximo.

É sua tarefa determinar como implementar esses dois pontos de sincronização. Note que os dados recebidos pela thread do servidor (identificador e descrição do problema do paciente) precisam estar disponíveis para a thread principal após o primeiro ponto de sincronização. A forma como essa transferência é feita fica a seu critério.

Caso o registro do médico retorne com -1 ou a chamada de um paciente retorne com um identificador menor que um o médico deve terminar sua execução (incluindo o servidor do consultório) depois de escrever a mensagem MI ou MCPR, conforme o caso.
Mensagens escritas pelo médico/consultório

    início da execução: 
        "MI(%4.1f) x %3.1f @ %d = %d" % (identificador do médico, tempo de atendimento, porto usado pelo servidor do consultório, valor de retorno do registro do médico)
    consulta:
        "CI(%4.1f,%s)" % (identificação do paciente, descrição do seu problema) - imediatamente ao iniciar o processamento da RPC da consulta 
        "CR(%4.1f,%4.1f)" % (identificação do paciente, identificação do médico) - ao final da consulta, imediatamente antes de retornar
    execução do médico: 
        "MCPI" - imediatamente antes de executar a chamada de um paciente (o médico já escreveu seu identificador ao iniciar)
        "MCPR -> %4.1f" % (identificador do paciente) - imediatamente ao retornar da chamada de um paciente 
        "MAI(%4.1f,%s)" % (identificador do paciente, descrição do seu problema) - início do atendimento, depois da chegada do paciente a consulta, antes de suspender o processo do médico
        "MAF" - ao final do atendimento, depois de liberar o paciente da sincronização na consulta
        "MT " - ao final do expediente, se recebe a mensagem de final no ambulatório

 
O cliente (o paciente)

O processo do paciente será um cliente de RPC padrão. Ele deve ser iniciado com quatro parâmetros: seu identificador (tipo_ident), um string descrevendo seu problema, o endereço (tipo_ender) e o número da porta (tipo_porto) onde ele encontrará o ambulatório. O cliente deve então executar o procedimento procura por um médico, que vai lhe devolver a localização de um consultório. Se o valor do porto for igual a zero, o cliente deve terminar. Caso contrário, ele deve executar o procedimento consulta com o servidor identificado, fornecendo seu identificador e o string com seu problema. Quando o procedimento retornar o paciente termina sua execução.
Mensagens escritas pelo paciente

Neste caso, há apenas uma sequência de mensagens:

    execução do paciente: 
        "PI(%4.1f,%s)" % (identificador do paciente, descrição do seu problema) - ao iniciar
        "PPMR(%s:%d)" % (endereço do servidor de consultório, porto) - imediatamente ao retornar de procura por um médico
        "PT -> %4.1f" % (valor de retorno (identificador do médico)) - imediatamente ao retornar da consulta, antes de terminar

O fim do expediente

O último programa necessário é um cliente simples cuja única função é acionar o procedimento término no servidor de ambulatório. Ele deve ser iniciado com dois parâmetros: o endereço (tipo_ender) e o número da porta (tipo_porto) onde se encontra o ambulatório. Após receber a resposta, termina sua execução.
Mensagens escritas pelo paciente

Neste caso, há apenas duas mensagens:

    execução do paciente: 
        "FE(%s,%d)" % (endereço do servidor, número da porta usada) - ao iniciar 
        "FE -> %d" % (valor de retorno) — imediatamente ao retornar do procedimento término, antes de terminar

Requisitos não funcionais:

O código deve ser escrito exclusivamente em Python 3, usando apenas as seguintes bibliotecas e módulos:

    grpcio e grpcio-tools: para a implementação do RPC;
    threading: para criação de threads e sincronização — especificamente, são permitidos Thread, Lock, Condition e Semaphore;
    time: usado internamente pelo módulo mytimer.py fornecido;
    módulos da biblioteca padrão que não ofereçam mecanismos de sincronização ou comunicação entre processos/threads além dos listados acima: sys, os, socket (apenas para resolução de nomes), e similares.

Além disso, bibliotecas mencionadas nas orientações sobre comportamentos especiais, como o fim do servidor e o pool de threads, podem ser usadas para esses fins específicos. Não são permitidos, em particular: asyncio e qualquer forma de E/S assíncrona; multiprocessing; queue.Queue e estruturas similares que encapsulem sincronização; e qualquer biblioteca externa além do gRPC. O uso de recursos não listados acima deve ser previamente autorizado pelo professor.

O material desenvolvido por você deve executar sem erros nas máquinas linux do laboratório de graduação. A correção será feita naquelas máquinas e programas que não compilarem, não seguirem as determinações quanto a nomes, parâmetros de entrada e formato da saída, ou apresentarem erros durante a execução serão desconsiderados. No momento, as máquinas estão instaladas com Python 3.8.10 (python3) e gRPC 1.70.0.
Data de entrega:

Confira na programação da disciplina.
O que deve ser entregue:

Você deve entregar um arquivo .zip contendo sete arquivos: os dois arquivos .proto descrevendo as interfaces do ambulatório e do consultório (um arquivo para a interface de cada servidor), arquivos com sua implementação (paciente.py, medico.py, ambulatorio.py e fim_de_expediente.py) e um Makefile como descrito a seguir. Você não deve incluir o arquivo mytimer.py na sua entrega, pois uma versão própria será usada nesse caso.

Considerando a simplicidade do sistema, um relatório final em PDF é opcional, caso você ache importante documentar decisões de projeto, especialmente as soluções de sincronização adotadas. Em qualquer caso, todo o código deve ser adequadamente comentado.

Preste atenção nos prazos: entregas com atraso poderão não ser aceitas.
O makefile a ser entregue:

Junto com o código deve ser entregue um makefile que inclua, pelo menos, as seguintes regras:

    clean - remove os arquivos gerados pelo compilador de stubs, deixando apenas os arquivos produzidos por você para e entrega
    stubs - faz a compilação dos arquivos de descrição dos dois protocolos, gerando os stubs

O módulo de controle de tempo e mensagens:

Junto com esse enunciado você vai encontrar um arquivo mytimer.py que fornece as funções my_sleep(tipo_tempo) e tstamp_msg(string). Elas devem ser usadas para suspender uma thread por um tempo determinado e para gerar as mensagens de saída dos diversos programas, respectivamente. Apenas mensagens geradas por tstamp_msg devem aparecer na saída, nos momentos indicados na descrição do funcionamento dos programas.
Referências úteis

Em um primeiro uso de gRPC, pode ser que vocês encontrem diversos pontos que vão exigir um pouco mais de atenção no estudo da documentação para conseguir fazer a implementação correta. Eu considero que os pontos que podem dar mais trabalho e que merecem algumas dicas são os seguintes:

identificação do endereço de um cliente

No registro do médico, o médico informa a porta do consultório, mas o próprio servidor de ambulatório pode identifiar diretamente o endereço da máquina onde está o médico, através do contexto da chamada de RPC que o médico executa. Para isso, basta que seja chamada a função peer() do parâmetro de contexto do procedimento. Por exemplo, para o procedimento say_hello mostrado nos exemplos, seu início seria:

def say_hello(self, request, context):
    client_addr=context.peer()

O formato retornado por context.peer() é definido na documentação do gRPC, mas basicamente é um string com três partes separadas por "dois pontos": a identificação do tipo de endereço (IPv4 ou IPv6), o endereço propriamente dito e o número do porto. Se o endereço for IPv6, ele mesmo contém um ou mais sinais de dois pontos e pode ser certado por colchetes. Para lidar com esses detalhes, a função a seguir pode ser usada para fazer o processamento dessa string para retirar corretamente o string do endereço e o número do porto:

    def split_peer(addr_str: str):
    # Remove gRPC's transport prefix, if present.
    if addr_str.startswith(("ipv4:", "ipv6:")):
        addr_str = addr_str.split(":", 1)[1]

    address, separator, port = addr_str.rpartition(":")
    # Remove brackets around an IPv6 address.
    if address.startswith("[") and address.endswith("]"):
        address = address[1:-1]

    return address, int(port)

Desligar um servidor através de um RPC

Como mencionado anteriormente, fazer um servidor de RPC parar de funcionar usando uma chamada de procedimento dele mesmo tem uma pegadinha: não basta chamar um exit() enquanto se executa o código do procedimento, ou ele vai terminar a execução antes de retornar da chamada, deixando o cliente sem resposta. E normalmente a gente só pode escrever código dentro das chamadas, já que não devemos alterar o código do stub. Cada framework de RPC tem uma solução diferente para esse problema e a solução do gRPC é bastante elegante, exigindo pouco código. Usa-se a geração de um evento dentro do código da RPC, que é capturado pelo servidor. Pode parecer complicado, mas o código para se fazer isso já está descrito no stackexchange (https://stackoverflow.com/questions/59262044/how-to-shutdown-grpc-server-from-grpc-client-in-python) . Um ponto importante é que pode ser necessário esperar um tempo para o procedimento que foi disparado pelo cliente realmente terminar. Esperar um segundo deve ser suficiente nesse caso.

Para garantir que o servidor não termine antes que todos os procedimentos em execução tenham retornado, cada procedimento do ambulatório, exceto o de terminação, deve incrementar um contador global de chamadas ativas logo ao iniciar, e decrementá-lo imediatamente antes de retornar. O procedimento término deve, após notificar médicos e pacientes em espera, aguardar até que esse contador chegue a zero antes de sinalizar o encerramento do servidor. Um único mutex protegendo o contador e uma variável de condição associada a ele são suficientes para isso — ou, alternativamente, o mesmo mutex que protege as filas pode ser reutilizado para esse fim, desde que o contador seja verificado dentro da mesma seção crítica. 
