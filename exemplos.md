# Exemplos de execução

Veja a seguir dois casos de uso do sistema: um onde um médico chega primeiro e outro onde um paciente chega primeiro. Em ambos os casos, o ambulatório é configurado com duas cadeiras e dois médicos, mas há apenas um paciente e um médico.

## Caso 1: médico chega primeiro.

O script a seguir pode ser usado para disparar os processos que precisam ser executados, na ordem correta:

```bash
echo "Ambulatório: 2 cadeiras, 2 médicos, porto 9999"
python3 ambulatorio.py 2 2 9999 > amb.out 2>&1 &

echo Médico
python3 medico.py 9991 99.1 2 localhost 9999 > med1.out 2>&1 &

sleep 1

echo "Paciente"
python3 paciente.py 6.1 enxaqueca localhost 9999 > pac1.out 2>&1 &

sleep 5

echo "Fim do expediente"
python3 fim_do_expediente.py localhost 9999 > fim.out 2>&1
```

Os arquivos gerados nessa execução seriam os apresentados a seguir. Os timestamps podem variar ligeriramente devido aos tempos em que os processos realmente executam. Em alguns casos, mensagens que aparecem no mesmo timestamp pode aparecer em ordem diferente a cada execução.

O string "%5B::1%5D" que aparece em algumas mensagens é a representação do endereço do host local em IPv6, que está ativado nas máquinas do laboratório de micros do DCC.

### amb.out

```txt
    0.0: mytime started at Mon Oct 12 16:15:41 2026
    0.0: AMB(2,2)@9999
    0.0: RM(99.1) @ %5B::1%5D:9991 = 0
    0.0: CP(99.1)
    0.0: CP(99.1) ESPERA
    1.0: PM( 6.1)
    1.0: PM( 6.1) -> M(99.1) @ %5B::1%5D:9991
    1.0: CP(99.1) -> P( 6.1)
    3.0: CP(99.1)
    3.0: CP(99.1) ESPERA
    6.0: TE
    6.0: CP(99.1) -> P( 0.0)
    6.0: TE -> 1
```

### med1.out

```txt
    0.0: mytime started at Mon Oct 12 16:15:41 2026
    0.0: SC(99.1) x 2.0 @ 9991
    0.0: AMB
    1.0: AMB -> 6.1
    1.0: CC( 6.1)
    1.0: CM( 6.1,enxaqueca)
    3.0: CT -> 0
    3.0: AMB
    3.0: CM( 6.1) -> 0
    6.0: AMB -> 0.0
```

### pac1.out

```txt
    0.0: mytime started at Mon Oct 12 16:15:42 2026
    0.0: P( 6.1,enxaqueca)
    0.0: CM(%5B::1%5D:9991)
    2.0: CT -> 0
```

### fim.out

```txt
    0.0: mytime started at Mon Oct 12 16:15:47 2026
    0.0: FE(localhost:9999)
    0.0: FE -> 1
```

## Caso 2: paciente chega primeiro.

O script a seguir pode ser usado para disparar os processos que precisam ser executados, na ordem correta:

```bash
echo "Ambulatório: 2 cadeiras, 2 médicos, porto 9999"
python3 ambulatorio.py 2 2 9999 > amb.out 2>&1 &

sleep 1

echo "Paciente"
python3 paciente.py 6.1 dengue localhost 9999 > pac1.out 2>&1 &

sleep 1

echo Médico
python3 medico.py 9991 99.1 2 localhost 9999 > med1.out 2>&1 &

sleep 5

echo "Fim do expediente"
python3 fim_do_expediente.py localhost 9999 > fim.out 2>&1
```

### amb.out

```txt
    0.0: mytime started at Mon Oct 12 16:20:47 2026
    0.0: AMB(2,2)@9999
    1.0: PM( 6.1)
    1.0: PM( 6.1) ESPERA
    2.0: RM(99.1) @ %5B::1%5D:9991 = 0
    2.0: CP(99.1)
    2.0: CP(99.1) -> P( 6.1)
    2.0: PM( 6.1) -> M(99.1) @ %5B::1%5D:9991
    4.0: CP(99.1)
    4.0: CP(99.1) ESPERA
    7.0: TE
    7.0: CP(99.1) -> P( 0.0)
    7.0: TE -> 1
```

### pac1.out

```txt
    0.0: mytime started at Mon Oct 12 16:20:48 2026
    0.0: P( 6.1,dengue)
    1.0: CM(%5B::1%5D:9991)
    3.0: CT -> 0
```

### med1.out

```txt
    0.0: mytime started at Mon Oct 12 16:20:49 2026
    0.0: SC(99.1) x 2.0 @ 9991
    0.0: AMB
    0.0: AMB -> 6.1
    0.0: CC( 6.1)
    0.0: CM( 6.1,dengue)
    2.0: CT -> 0
    2.0: AMB
    2.0: CM( 6.1) -> 0
    5.0: AMB -> 0.0
```

### fim.out

```txt
    0.0: mytime started at Mon Oct 12 16:20:54 2026
    0.0: FE(localhost:9999)
    0.0: FE -> 1
```
