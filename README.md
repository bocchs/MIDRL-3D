## Multitask radiological modality invariant landmark localization using deep reinforcement learning

This work presents multitask modality invariant deep reinforcement learning framework (MIDRL) for landmark localization across multiple different orgrans (in a single volume) and modalities using a multiple reinforcement learning agents. 

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
To cite this work:
Parekh VS, E. BA, Braverman V, Jacobs MA: Multitask radiological modality invariant landmark localization using deep reinforcement learning. In: Proceedings of the Third Conference on Medical Imaging with Deep Learning. vol. 121. Proceedings of Machine Learning Research: PMLR; 2020: 588--600.

### References
[1] Athanasios Vlontzos, Amir Alansary, Konstantinos Kamnitsas, Daniel Rueckert, and Bern-hard Kainz.  Multiple landmark detection using multi-agent reinforcement learning.  InInternational Conference on Medical Image Computing and Computer-Assisted Interven-tion, pages 262–270. Springer, 2019
