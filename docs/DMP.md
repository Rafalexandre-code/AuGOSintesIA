# Plano de Gestão de Dados (DMP) — GO–AuNP sob variabilidade multi-fonte de matéria-prima

Projeto de IC FAPESP, UNESP-IQ Araraquara (SisPlexos). Versão 0.1 (RASCUNHO, 2026-10-01) — revisar com o
orientador e anexar à submissão. Estrutura conforme as orientações da FAPESP para planos de gestão de dados.

**1. Dados gerados e reutilizados.**
(a) *Medidos*: lotes de GO e de reagentes, análises de impurezas, caracterização do GO (XPS, Raman, FTIR, XRD,
DLS/zeta, AFM), 60 sínteses independentes + controles, espectros UV-Vis brutos (2 leituras/síntese), imagens de TEM,
DLS; formato CSV (UTF-8) e arquivos nativos dos instrumentos (.dm3/.dm4, .vms, .spc…) — estimativa: < 20 GB.
(b) *Derivados*: descritores por lote com incerteza, perda espectral J, desfechos, resultados de QC, propostas do
otimizador, simulações de campanha (marcadas SIMULADO). (c) *Reutilizados*: Cruse et al. 2022 (figshare), NSP Database
(Gu et al. 2026, Hugging Face), AuNCs (Zenodo), JARVIS-DFT — com licença e citação em `tools/data_sources/sources.tsv`.

**2. Documentação e metadados.** Modelo de dados com 13 tabelas, dicionário e JSON Schema
(`datasets/data-model/`, validador `tools/data_sources/lab_data_model.py`); unidades SI/UO e incerteza (valor, tipo,
nº de réplicas) em toda medida; termos de ontologia eNanoMapper/CHMO quando aplicável; SOPs versionados
(`datasets/lab/protocols/`); plano de análise pré-registrado com selo sha256 (`config/preregistration.yaml`);
proveniência computacional por execução (commit, pacotes, semente, hash das tabelas: `run_metadata.json`) e
**Instance Maps** em RO-Crate/JSON-LD com termos W3C PROV (`tools/data_sources/instance_map.py`).

**3. Qualidade.** Validação de esquema e QC automático (`code/qc/qc_check.py`, critérios em
`config/qc_criteria.yaml`, cartas de controle Shewhart/EWMA nos controles); falhas e resultados negativos permanecem
no registro (`status=failed`); dados minerados da literatura com auditoria por amostragem
(`tools/data_sources/audit_extraction.py`).

**4. Compartilhamento e acesso.** Dados medidos, código e protocolos serão abertos ao fim do projeto ou na
publicação (o que vier primeiro), em depósito com DOI por versão no **Zenodo** (`deposit/GO-AuNP-Autonomous-Design/`,
montagem por `tools/data_sources/build_deposit.py`), espelhado no NIST MDR/MDF quando viável; licenças: **CC BY 4.0**
(dados) e **MIT** (código próprio). Restrições: dados de terceiros seguem a licença original (só os autorizados são
redistribuídos; os demais por referência/DOI); nenhum dado pessoal é coletado.

**5. Armazenamento, cópia de segurança e preservação.** Durante o projeto: repositório Git privado no GitHub
(histórico completo) + cópia institucional da UNESP; arquivos brutos grandes fora do Git, com sha256 no MANIFEST do
depósito. Após o projeto: Zenodo (preservação de longo prazo, CERN) por ≥ 20 anos; o código também fica no GitHub
com o DOI do Zenodo.

**6. Responsáveis e custos.** Bolsista: registro diário, validação e QC (SOP-DATA-01); orientador: revisão mensal e
aprovação de emendas ao pré-registro e do depósito. Sem custo adicional (Zenodo e GitHub gratuitos).
