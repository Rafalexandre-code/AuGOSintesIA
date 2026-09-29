# UV-Vis Module


## Introduction
<p align="center">
  <img src="img\UVPlatform_architecture.png" width="70%" height="70%" />
</p>

This repository contains source code of UV-Vis hardware for nanoparticle analysis. We follow [OpenLH [1]](https://www.instructables.com/OpenLH/) and construct system based on robotic settings. This system is controlled by [BespokeSynthesisPlatform](https://github.com/KIST-CSRC/BespokeSynthesisPlatform)

## Device settings

- Pipette machine (uArm Swift Pro)
- Pipette pump (NEMA 17 motor + Arduino)
- UV spectrometer (Ocean optics USB2000+)
- Light soucre (Ocean optics)
- Camera (Logitech C920)
- Cuvette storage
- Cuvette holder
- Vial holder

## Video
<p align="center">
  <img src="img\UV_PipetteMachine.gif" width="70%" height="70%" />
</p>

This hardware was reffered by OpenLH.[1]


## Installation

**Using conda**
```bash
conda env create -f requirements_conda.txt
```
**Using pip**
```bash
pip install -r requirements_pip.txt
```

## Script architecture
```
UV-VisModule
├── BaseUtils
│   └── Preprocess.py
│   └── TCP_Node.py
├── Dataset
├── img
├── Log
│   └── Logging_Class.py
├── Pipette_Machine
│   └── serial_labware
│       └── serial_labware.py
│   └── hotplate.py
│   └── IKA_RET_Control_Visc.py
├── SafetyProtocol
│   └── model
│       └── denseSSD.py
│       └── MultiBoxLoss.py
│   └── pretrained
│       └── model_best.pth
│   └── Syringe_Pump_Package
│   └── utils
│       └── convert_xml2txt.py
│       └── data_splitting.py
│       └── image_process.py
│       └── pinDataset.py
│       └── vialStorageDataset.py
│   └── config_denseSSD.py
│   └── detect_DenseSSD.py
├── Spectrometer_client
│   └── UV_Class.py
├── Spectrometer_server
│   └── insert_json.py
│   └── jsoncpp.cpp
│   └── JSONWriter.h
│   └── TCPServer.cpp
│   └── TCPServer.h
│   └── UV_GPIO.cpp
│   └── UV_Server_Connection.cpp
│   └── UV_Server_Connection.sln
└── UVServer.py
```

## Reference
1. Gome, Gilad, et al. "OpenLH: open liquid-handling system for creative experimentation with biology." Proceedings of the Thirteenth International Conference on Tangible, Embedded, and Embodied Interaction. 2019.
2. Yoo, H. J., Kim, N., Lee, H., Kim, D., Ow, L. T. C., Nam, H., ... & Han, S. S. (2023). Bespoke Nanoparticle Synthesis and Chemical Knowledge Discovery Via Autonomous Experimentations. arXiv preprint arXiv:2309.00349.
