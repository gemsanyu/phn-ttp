import argparse

def get_parser():
    parser = argparse.ArgumentParser(description='TTP-MORL')
    # GENERAL
    parser.add_argument('--dataset-name',
                        type=str,
                        default="eil76-n75",
                        help="dataset's name for real testing")
    parser.add_argument('--title',
                        type=str,
                        default="init-sop",
                        help="title for experiment")
    parser.add_argument('--device',
                        type=str,
                        default='cpu',
                        help='device to be used cpu or cuda(gpu)')
    parser.add_argument('--num-items-per-city',
                        nargs='+',
                        type=int,
                        default=[1,3,5],
                        help='number of items per city')
    parser.add_argument('--num-nodes',
                        type=int,
                        default=50,
                        help='num nodes/num cities')
    parser.add_argument('--max-epoch',
                        type=int,
                        default=100000,
                        help='maximum epoch training')
    parser.add_argument('--seed',
                        type=int,
                        default=1,
                        help='seed for random generator')
    parser.add_argument('--batch-size',
                        type=int,
                        default=64,
                        help="dataloader batch size")
    parser.add_argument('--num-training-samples',
                        type=int,
                        default=1000,
                        help="total training instances")
    parser.add_argument('--num-validation-samples',
                        type=int,
                        default=1000,
                        help="total validation instances")
    
    # Agent
    parser.add_argument('--max-grad-norm',
                        type=int,
                        default=1,
                        help="gradient clipping")
    parser.add_argument('--lr',
                        type=float,
                        default=1e-4,
                        help="learning rate")
    parser.add_argument('--encoder-size',
                        type=int,
                        default=128,
                        help='Encoder layer\'s size.')
    parser.add_argument('--pointer-layers',
                        type=int,
                        default=2,
                        help='Total layer(s) for pointer.')
    parser.add_argument('--pointer-neurons',
                        nargs='?',
                        type=int,
                        default=None,
                        help='Total neurons for pointer.')
    parser.add_argument('--dropout',
                        type=float,
                        default=0.2,
                        help='Dropout.')
    parser.add_argument('--n-glimpses',
                        type=int,
                        default=1,
                        help="num of repetition for glimpse computation")

    # PHN
    parser.add_argument('--num-ray',
                        type=int,
                        default=128,
                        help="number of rays in training")
    parser.add_argument('--ld',
                        type=int,
                        default=4,
                        help="lambda for cosine penalty")
    parser.add_argument('--ray-hidden-size',
                        type=int,
                        default=128,
                        help="ray hidden size")
    parser.add_argument('--omega',
                        type=int,
                        default=10,
                        help="max patience")

    return parser
