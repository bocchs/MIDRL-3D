# Multiple Anatomical Landmark Detection using Multi-agent RL

Automatic detection of anatomical landmarks is an important step for a wide range of applications in medical image analysis. The location of anatomical landmarks is interdependent and non-random in a human anatomy, hence locating one is able to help locate others. In this project, we formulate the landmark detection problem as a cocurrent partially observable markov decision process (POMDP) navigating in a medical image environment towards the target landmarks. We create a collaborative Deep Q-Network (DQN) based architecture where we share the convolutional layers amongst agents, sharing thus implicitly knowledge. This code also supports both fixed- and multi-scale search strategies with hierarchical action steps in a coarse-to-fine manner.

* Code is part of [Tensorpack-medical project](https://github.com/amiralansary/tensorpack-medical). 

<p align="center">
<img style="float: center;" src="images/Colab_dqn_BW.png" width="465">
<img style="float: center;" src="images/actions.png" width="250">
</p>



---
## Results
Example of the multi-agent model locating the kidney, trochanter, heart, and knee in a 3D whole body Dixon water MRI. Red is the target bounding box, yellow is the multi-agent bounding box.


<p align="center">
<img src="./images/normal6_W.gif">
</p>


---



## Usage
```
usage: DQN.py [-h] [--gpu GPU] [--load LOAD] [--task {play,eval,train}]
              [--files FILES [FILES ...]] [--saveGif] [--saveVideo]
              [--logDir LOGDIR] [--name NAME] [--agents AGENTS]

optional arguments:
  -h, --help            show this help message and exit
  --gpu GPU             comma separated list of GPU(s) to use.
  --load LOAD           load model
  --task {play,eval,train}
                        task to perform. Must load a pretrained model if task
                        is "play" or "eval"
 
  --files FILES [FILES ...]
                        Filepath to the text file that comtains list of
                        images. Each line of this file is a full path to an
                        image scan. For (task == train or eval) there should
                        be two input files ['images', 'landmarks']
  --saveGif             save gif image of the game
  --saveVideo           save video of the game
  --logDir LOGDIR       store logs in this directory during training
  --name NAME           name of current experiment for logs
  --agents AGENTS       number of agents to be trained simulteniously 
```

### Train
```
 python DQN.py --task train  --gpu 0 --files './data/filenames/image_files.txt' './data/filenames/landmark_files.txt'
```

### Evaluate
```
python DQN.py --task eval  --gpu 0 --load data/models/DQN_multiscale_brain_mri_point_pc_ROI_45_45_45/model-600000 --files './data/filenames/image_files.txt' './data/filenames/landmark_files.txt'
```

### Test
```
python DQN.py --task play  --gpu 0 --load data/models/DQN_multiscale_brain_mri_point_pc_ROI_45_45_45/model-600000 --files './data/filenames/image_files.txt'
```

### Citation 
To cite this work use the below bibtex item.
https://arxiv.org/pdf/1907.00318.pdf
```
@article{Vlontzos2019,
author = {Vlontzos, Athanasios and Alansary, Amir and Kamnitsas, Konstantinos and Rueckert, Daniel and Kainz, Bernhard},
title = {Multiple Landmark Detection using Multi-Agent Reinforcement Learning},
journal={MICCAI}
year = {2019}
}
```
