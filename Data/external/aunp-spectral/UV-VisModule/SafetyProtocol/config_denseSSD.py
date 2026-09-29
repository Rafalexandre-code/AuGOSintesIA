# GPU Device
device = "cuda:0"

# Path to data dir
image_dir = 'our_dataset/img/'
train_label = 'train_p.txt'
val_label = 'valid_p.txt'

# Training hyper parameters
init_lr = 0.001
momentum = 0.9
num_epochs = 100
batch_size = 8
weight_decay = 5e-4
pretrained = True
model_path = 'pretrained/model_latest.pth'
image_size = 300
C = 2
