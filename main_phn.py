import random
import subprocess
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader
from torch.nn.functional import cosine_similarity
from tqdm import tqdm

from arguments import get_parser
from setup import setup_phn
from solver.hv_maximization import HvMaximization
from ttp.ttp_dataset import TTPDataset
from ttp.ttp_env import TTPEnv
from utils import update_phn, write_training_phn_progress, save_phn
from utils import solve_decode_only

CPU_DEVICE = torch.device("cpu")

def prepare_args():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    args.device = torch.device(args.device)
    return args

def train_one_batch(batch, agent, phn, phn_opt, writer, num_ray=16, ld=1):
    
    coords, norm_coords, W, norm_W, profits, norm_profits, weights, norm_weights, min_v, max_v, max_cap, renting_rate, item_city_idx, item_city_mask, best_profit_kp, best_route_length_tsp = batch
    env = TTPEnv(coords, norm_coords, W, norm_W, profits, norm_profits, weights, norm_weights, min_v, max_v, max_cap, renting_rate, item_city_idx, item_city_mask, best_profit_kp, best_route_length_tsp)
    mo_opt = HvMaximization(n_mo_sol=num_ray, n_mo_obj=2)
    
    start = 0.1
    end = np.pi/2-0.1    

    ray_list = []
    profit_loss_list = []
    length_loss_list = []
    # across rays, the static embeddings are the same, so reuse
    # and dont record grads of encodings, maybe...
    with torch.no_grad():
        static_features = env.get_static_features()
        static_features = torch.from_numpy(static_features).to(agent.device)
        item_init_embed = agent.item_init_embedder(static_features[:, :env.num_items, :])
        depot_init_embed = agent.depot_init_embed.expand(size=(env.batch_size,1,-1))
        node_init_embed = agent.node_init_embed.expand(size=(env.batch_size,env.num_nodes-1,-1))
        init_embed = torch.cat([item_init_embed, depot_init_embed, node_init_embed], dim=1)
        static_embeddings, graph_embeddings = agent.gae(init_embed)
        fixed_context = agent.project_fixed_context(graph_embeddings)
        glimpse_K_static, glimpse_V_static, logits_K_static = agent.project_embeddings(static_embeddings).chunk(3, dim=-1)
        glimpse_K_static = agent._make_heads(glimpse_K_static)
        glimpse_V_static = agent._make_heads(glimpse_V_static)

    for i in range(num_ray):
        r = np.random.uniform(start + i*(end-start)/num_ray, start+ (i+1)*(end-start)/num_ray)
        ray = np.array([np.cos(r),np.sin(r)], dtype='float32')
        ray /= ray.sum()
        ray *= np.random.randint(1, 5)*abs(np.random.normal(1, 0.2))
        ray = torch.from_numpy(ray).to(agent.device)
        param_dict = phn(ray)

        solve_output = solve_decode_only(agent, env, static_embeddings, fixed_context, glimpse_K_static, glimpse_V_static, logits_K_static, param_dict)
        tour_list, item_selection, tour_lengths, total_profits, total_costs, logprobs, sum_entropies = solve_output
        agent.eval()
        with torch.no_grad():
            critic_output = solve_decode_only(agent, env, static_embeddings, fixed_context, glimpse_K_static, glimpse_V_static, logits_K_static, param_dict)
            _, _, critic_lengths, critic_profits, _, _, _ = critic_output    
        agent.train()
        agent.gae.eval()
        profit_loss = (critic_profits-total_profits).to(agent.device)*logprobs
        length_loss = (tour_lengths-critic_lengths).to(agent.device)*logprobs
        profit_loss_list.append(profit_loss)
        length_loss_list.append(length_loss)
        ray_list.append(ray)

    profit_loss_list = torch.stack(profit_loss_list)
    length_loss_list = torch.stack(length_loss_list)
    loss_list = torch.cat([length_loss_list.unsqueeze(2), profit_loss_list.unsqueeze(2)],dim=2)
    profit_loss_max, _ = torch.max(profit_loss_list,dim=0)
    profit_loss_min, _ = torch.min(profit_loss_list,dim=0)
    length_loss_max, _ = torch.max(length_loss_list,dim=0)
    length_loss_min, _ = torch.min(length_loss_list,dim=0)
    profit_loss_min, profit_loss_max = profit_loss_min.unsqueeze(0), profit_loss_max.unsqueeze(0)
    length_loss_min, length_loss_max = length_loss_min.unsqueeze(0), length_loss_max.unsqueeze(0)
    norm_profit_loss_list = (profit_loss_list-profit_loss_min)/(profit_loss_max-profit_loss_min)
    norm_length_loss_list = (length_loss_list-length_loss_min)/(length_loss_max-length_loss_min)
    norm_obj = torch.cat([norm_length_loss_list.unsqueeze(2), norm_profit_loss_list.unsqueeze(2)],dim=2)
    norm_obj = norm_obj.detach().cpu().numpy()
    ray_list = torch.stack(ray_list)
    hv_drv_list = [] 
    for i in range(env.batch_size):
        obj_instance = np.transpose(norm_obj[:, i, :]) 
        hv_drv_instance = mo_opt.compute_weights(obj_instance).transpose(0,1).unsqueeze(1)
        hv_drv_list.append(hv_drv_instance)
    hv_drv_list = torch.cat(hv_drv_list, dim=1).to(agent.device)
    losses_per_obj = loss_list*hv_drv_list
    losses_per_instance = torch.sum(losses_per_obj, dim=2)
    losses_per_ray = torch.mean(losses_per_instance, dim=1)
    total_loss = torch.sum(losses_per_ray)
    
    # compute cosine similarity penalty
    cos_penalty = cosine_similarity(loss_list, ray_list.unsqueeze(1), dim=2)
    total_loss += ld*cos_penalty.sum()
    update_phn(phn, phn_opt, total_loss)
    agent.zero_grad(set_to_none=True)
    phn.zero_grad(set_to_none=True)
    write_training_phn_progress(writer,loss_list.detach().cpu(),ray_list.cpu(),cos_penalty.detach().cpu())

def train_one_epoch(agent, phn, phn_opt, train_dataset, writer, num_ray=8):
    agent.train()
    phn.train()
    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size, num_workers=4, pin_memory=True, shuffle=True)
    for batch_idx, batch in tqdm(enumerate(train_dataloader), desc="Training", position=1):
    # for batch_idx, batch in enumerate(train_dataloader):
        train_one_batch(batch, agent, phn, phn_opt, writer, num_ray)

def run(args):
    agent, phn, phn_opt, last_epoch, writer, checkpoint_path, test_env, test_sample_solutions = setup_phn(args)
    num_nodes_list = [20,30]
    num_items_per_city_list = [1,3,5]
    config_list = [(num_nodes, num_items_per_city) for num_nodes in num_nodes_list for num_items_per_city in num_items_per_city_list]
    num_configs = len(num_nodes_list)*len(num_items_per_city_list)
    test_proc = None
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
        save_phn(phn, phn_opt, epoch, checkpoint_path)
        if test_proc is not None:
            test_proc.wait()
        # test_proc_cmd = "python validate.py --title "+ args.title + " --dataset-name "+ args.dataset_name + " --device cpu"
        test_proc_cmd = ["python",
                        "validate_phn.py",
                        "--title",
                        args.title,
                        "--dataset-name",
                        args.dataset_name,
                        "--device",
                        "cpu"]
        test_proc = subprocess.Popen(test_proc_cmd)
        # test_one_epoch(agent,phn,test_env,test_sample_solutions,writer,epoch,n_solutions=10)
    if test_proc is not None:
        test_proc.wait()

if __name__ == '__main__':
    # torch.backends.cudnn.enabled = False
    args = prepare_args()
    torch.set_num_threads(6)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    run(args)