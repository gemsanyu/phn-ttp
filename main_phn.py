from cgi import test
import os
import random
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader, random_split
from torch.nn.functional import cosine_similarity
from tqdm import tqdm

from arguments import get_parser
from setup import setup_phn
from solver.hv_maximization import HvMaximization
from ttp.ttp_dataset import TTPDataset
from ttp.ttp_env import TTPEnv
from utils import update_phn, write_test_phn_progress, write_training_phn_progress, save_phn
from utils import solve_decode_only

CPU_DEVICE = torch.device("cpu")


def prepare_args():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    args.device = torch.device(args.device)
    return args

def train_one_batch(batch, agent, phn, phn_opt, writer, num_ray=16, ld=4):
    
    coords, norm_coords, W, norm_W, profits, norm_profits, weights, norm_weights, min_v, max_v, max_cap, renting_rate, item_city_idx, item_city_mask, best_profit_kp, best_route_length_tsp = batch
    env = TTPEnv(coords, norm_coords, W, norm_W, profits, norm_profits, weights, norm_weights, min_v, max_v, max_cap, renting_rate, item_city_idx, item_city_mask, best_profit_kp, best_route_length_tsp)
    mo_opt = HvMaximization(n_mo_sol=num_ray, n_mo_obj=2)
    
    start = 0.1
    end = np.pi/2-0.1    

    ray_list = []
    profit_list = []
    length_list = []
    logprob_list = []
    
    # across rays, the static embeddings are the same, so reuse
    static_features = env.get_static_features()
    static_features = torch.from_numpy(static_features).to(agent.device)
    static_embeddings, graph_embeddings = agent.gae(static_features)

    for i in range(num_ray):
        r = np.random.uniform(start + i*(end-start)/num_ray, start+ (i+1)*(end-start)/num_ray)
        ray = np.array([np.cos(r),np.sin(r)], dtype='float32')
        ray /= ray.sum()
        ray *= np.random.randint(1, 5)*abs(np.random.normal(1, 0.2))
        ray = torch.from_numpy(ray).to(agent.device)
        param_dict = phn(ray)

        tour_list, item_selection, tour_lengths, total_profits, total_costs, logprobs, sum_entropies = solve_decode_only(agent, env, static_embeddings, graph_embeddings, param_dict)
        profit_list.append(total_profits)
        length_list.append(tour_lengths)
        logprob_list.append(logprobs)
        ray_list.append(ray)

    profit_list = torch.stack(profit_list)
    length_list = torch.stack(length_list)
    logprob_list = torch.stack(logprob_list).unsqueeze(2)
    ray_list = torch.stack(ray_list)
    batch_profit_max = torch.from_numpy(env.best_profit_kp).view(1,-1)
    norm_profit_list = profit_list/batch_profit_max
    batch_length_max, _ = torch.max(length_list, dim=0, keepdim=True)
    batch_length_min = torch.from_numpy(env.best_route_length_tsp).view(1,-1)
    norm_length_list = (length_list-batch_length_min)/(batch_length_max-batch_length_min)
    norm_profit_list = norm_profit_list
    norm_length_list = norm_length_list
    norm_objectives = torch.cat([norm_profit_list.unsqueeze(2), norm_length_list.unsqueeze(2)], dim=2)
    hv_drv_list = [] 
    import matplotlib.pyplot as plt
    for i in range(env.batch_size):
        obj_instance = norm_objectives[:, i, :].transpose(0,1).numpy()
        hv_drv_instance = mo_opt.compute_weights(obj_instance).transpose(0,1).unsqueeze(1)
        hv_drv_list.append(hv_drv_instance)
    hv_drv_list = torch.cat(hv_drv_list, dim=1).to(agent.device)
    norm_objectives = norm_objectives.to(agent.device)
    losses_per_obj = norm_objectives*hv_drv_list*logprob_list
    losses_per_instance = torch.sum(losses_per_obj, dim=2)
    losses_per_ray = torch.mean(losses_per_instance, dim=1)
    total_loss = torch.sum(losses_per_ray)
    
    # compute cosine similarity penalty
    cos_penalty = ld*cosine_similarity(norm_objectives, ray_list.unsqueeze(1), dim=2).sum()
    total_loss -= cos_penalty
    update_phn(phn, phn_opt, total_loss)
    agent.zero_grad(set_to_none=True)
    write_training_phn_progress(total_profits.mean(), tour_lengths.mean(), 0, 0, total_loss.detach().cpu(), logprobs.detach().cpu().mean(), env.num_nodes, env.num_items, writer)

def train_one_epoch(agent, phn, phn_opt, train_dataset, writer, num_ray=16):
    agent.train()
    phn.train()
    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size, num_workers=4, pin_memory=True, shuffle=True)
    for batch_idx, batch in tqdm(enumerate(train_dataloader), desc="Training", position=1):
    # for batch_idx, batch in enumerate(train_dataloader):
        train_one_batch(batch, agent, phn, phn_opt, writer, num_ray)

@torch.no_grad()
def test_one_epoch(agent, phn, test_env, test_sample_solutions, writer, epoch, n_solutions=100):
    agent.eval()
    phn.eval()
    ray_list = [torch.tensor([[float(i)/n_solutions,1-float(i)/n_solutions]]) for i in range(n_solutions)]
    solution_list = []
    # across rays, the static embeddings are the same, so reuse
    static_features = test_env.get_static_features()
    static_features = torch.from_numpy(static_features).to(agent.device)
    static_embeddings, graph_embeddings = agent.gae(static_features)
    for ray in tqdm(ray_list, desc="Testing"):
        param_dict = phn(ray.to(agent.device))
        tour_list, item_selection, tour_length, total_profit, total_cost, logprob, sum_entropies = solve_decode_only(agent, test_env, static_embeddings, graph_embeddings, param_dict)
        solution_list += [torch.stack([tour_length, total_profit], dim=1)]
    solution_list = torch.cat(solution_list)
    write_test_phn_progress(writer, solution_list, epoch, test_sample_solutions)

def run(args):
    agent, phn, phn_opt, last_epoch, writer, checkpoint_path, test_env, test_sample_solutions = setup_phn(args)
    num_nodes_list = [50]
    num_items_per_city_list = [1,3,5]
    config_list = [(num_nodes, num_items_per_city) for num_nodes in num_nodes_list for num_items_per_city in num_items_per_city_list]
    num_configs = len(num_nodes_list)*len(num_items_per_city_list)
    for epoch in range(last_epoch, args.max_epoch):
        config_it = epoch%num_configs
        if config_it == 0:
            random.shuffle(config_list)
        num_nodes, num_items_per_city = config_list[config_it]
        print("EPOCH:", epoch)
        print("CONFIG:",num_nodes,num_items_per_city)
        print("---------------------------------------")
        dataset = TTPDataset(args.num_training_samples, num_nodes, num_items_per_city)
        train_one_epoch(agent, phn, phn_opt, dataset, writer)
        test_one_epoch(agent, phn, test_env, test_sample_solutions, writer, epoch)
        save_phn(phn, phn_opt, epoch, checkpoint_path)

if __name__ == '__main__':
    # torch.backends.cudnn.enabled = False
    args = prepare_args()
    torch.set_num_threads(12)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    run(args)