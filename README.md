[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![arXiv](https://img.shields.io/badge/arXiv-2403.05478-b31b1b.svg)](https://arxiv.org/abs/2403.05478)

# HGIC: A Hand Gesture Based Interactive Control System for Efficient and Scalable Multi-UAV Operationss

Mengsha Hu, Jinzhou Li, Runxiang Jin, Chao Shi, Lei Xu, Rui Liu

![example](img/example.png)

This repository contains the code for the paper [HGIC](https://arxiv.org/abs/2403.05478)

## Code Structure

* `hand_recognition` folder contains the code for hand gesture recognition.
* `swarm_controller` folder contains the code for swarm control.
* `settings.json` file contains the settings for the AirSim simulator.

<!-- GETTING STARTED -->

## Requirements

* Install by running the following command.
  ```sh
  git clone https://github.com/kingchou007/HGIC_Platform
  ```
* Environment
  ```sh
  pip install -r requirements.txt
  ```

## AirSim Download and Installation

Please follow the instructions in the [AirSim](https://microsoft.github.io/AirSim/) website to download and install the AirSim simulator.

Once you have installed the AirSim simulator, please replace the `settings.json` file in the `Documents/AirSim` folder with the `settings.json` file in the `AirSim` folder in this repository.

## Running the Code

Please open the AirSim simulator. Then, Open two terminals and run the following commands in each terminal.

Terminal 1:

```sh
cd hand_recognition # Path: hand_recognition
python3 main.py
```

Terminal 2:

```sh
cd swarm_controller # Path: swarm_controller
python connect.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

* [AirSim](https://github.com/microsoft/AirSim)
* [Google Media-Pipe](https://github.com/google/mediapipe)
