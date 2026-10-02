# Simulações registradas (SIMULADO)

> **SIMULADO** — resumo gerado por `python code/benchmarking/campaign_sim.py report outputs/campaign_sim` a partir
> do laboratório simulado (`code/benchmarking/simulator.py`). Os números dimensionam e testam o protocolo; não são
> medidas nem previsões do ganho real.

Em execução: cenário principal (10 sementes × 13 braços × 12 rodadas), transferência para o lote reservado L4
(10 sementes) e MISO (8 sementes × MGP/ICM/PCM/só-TEM). Este arquivo é substituído pelo relatório quando terminarem.

Para reproduzir:

```bash
python code/benchmarking/campaign_sim.py --seeds 10 --rounds 12 --q 2 --workers 4
python code/benchmarking/campaign_sim.py --scenario transfer --seeds 10 --workers 4
python code/miso/miso.py benchmark --seeds 8 --workers 4
python code/benchmarking/campaign_sim.py report outputs/campaign_sim > docs/SIMULACOES.md
```
