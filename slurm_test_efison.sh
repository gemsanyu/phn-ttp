#!/bin/bash                      

#SBATCH --ntasks=4         # Contoh menggunakan 32 core CPU.
#SBATCH --mem=20GB               # Contoh menggunakan RAM 16GB.
#SBATCH --time=12:00:00          # Contoh menetapkan walltime maks 30 menit.
#SBATCH --output=logs/result-%j.out   # Output terminal program.
#SBATCH --error=logs/result-%j.err    # Output verbose program.
#SBATCH --partition=gpu_ampere     # Menggunakan Compute Node GPU 
#SBATCH --gres=gpu:1               # Menggunakan 1 GPU

module load Anaconda3/2022.05
module load cuda/11.6-cuDNN8.3.3

python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 1 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 2 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 3 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 4 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 5 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 6 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 7 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 8 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 9 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 10 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 11 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 12 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 13 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 14 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 15 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 16 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 17 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 18 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 19 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 20 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 21 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 22 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 23 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 24 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 25 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 26 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 27 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 28 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 29 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 30 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 31 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 32 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 33 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 34 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 35 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 36 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 37 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 38 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 39 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 40 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 41 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 42 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 43 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 44 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 45 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 46 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 47 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 48 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 49 --total-weight 50;
# python test_quantized.py --title att_drlmoa_luna --dataset-name fnl4461-n22300 --weight-idx 50 --total-weight 50;