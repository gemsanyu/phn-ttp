from random import random
import torch
import math
import inspect

import numpy as np
from typing import NamedTuple

from policy.non_dominated_sorting import fast_non_dominated_sort
from policy.hv import Hypervolume
from policy.normalization import normalize

CPU_DEVICE = torch.device('cpu')


def get_utility(n=10):
    n = float(n)
    idx = torch.arange(n, dtype=torch.float32) + 1
    u = math.log(n/2 + 1) - torch.log(idx)
    u = u * (1-(u < 0).float())
    u = u / torch.sum(u)
    u = u - 1/n
    return u


def get_utility_hansen(n=10):
    a = math.log(n/2. + 1.)
    rank = torch.arange(n) + 1
    b = torch.log(n-rank)
    utility = torch.clamp_min(a-b, 0)
    return utility


def get_hv_contributions(solution_list:np.array, reference_point=None):
    num_solutions, M = solution_list.shape
    if reference_point is None:
        reference_point = np.array([1.1,1.1])
    hv_getter = Hypervolume(reference_point)
    total_hv = hv_getter.calc(solution_list)
    # print(total_hv,"HV")

    if num_solutions == 1:
        return total_hv
    hv_contributions = np.zeros((num_solutions,), dtype=np.float32)
    solution_mask = np.full((num_solutions,), True)
    for i in range(num_solutions):
        solution_mask[i] = 0
        hv_without_sol = hv_getter.calc(solution_list[solution_mask])
        hv_contributions[i] = total_hv-hv_without_sol
        solution_mask[i] = 1
    return hv_contributions


def update_nondom_archive(curr_nondom_archive, f_list):
    if curr_nondom_archive is not None:
        f_list = torch.cat([curr_nondom_archive, f_list])
    nondom_idx = fast_non_dominated_sort(f_list.numpy())[0]
    return f_list[nondom_idx]

def combine_with_nondom(f_list, nondom_archive):
    exists_in_flist = torch.eq(nondom_archive.unsqueeze(1), f_list)
    exists_in_flist = exists_in_flist.any(dim=2).any(dim=1)
    combined_unique = torch.cat([f_list, nondom_archive[torch.logical_not(nondom_archive)]])
    return combined_unique

class BatchProperty(NamedTuple):
    num_nodes: int
    num_items_per_city: int
    num_clusters: int
    item_correlation: int
    capacity_factor: int


def get_batch_properties(num_nodes_list, num_items_per_city_list):
    """
        training dataset information for each batch
        1 batch will represent 1 possible problem configuration
        including num of node clusters, capacity factor, item correlation
        num_nodes, num_items_per_city_list
    """
    batch_properties = []
    capacity_factor_list = [i+1 for i in range(10)]
    num_clusters_list = [1]
    item_correlation_list = [i for i in range(3)]

    for num_nodes in num_nodes_list:
        for num_items_per_city in num_items_per_city_list:
            for capacity_factor in capacity_factor_list:
                for num_clusters in num_clusters_list:
                    for item_correlation in item_correlation_list:
                        batch_property = BatchProperty(num_nodes, num_items_per_city,
                                                       num_clusters, item_correlation,
                                                       capacity_factor)
                        batch_properties += [batch_property]
    return batch_properties


def custom_permute_2d(x, permutation):
    d1, d2 = x.size()
    ret = x[
        torch.arange(d1).unsqueeze(1).repeat((1, d2)).flatten(),
        permutation.flatten()
    ].view(d1, d2)
    return ret


def print_gpu_memory_usage():
    t = torch.cuda.get_device_properties(0).total_memory
    r = torch.cuda.memory_reserved(0)
    a = torch.cuda.memory_allocated(0)
    f = r-a  # free inside reserved

    caller_name = inspect.stack()[1][3]
    print("------------------------")
    print("In Function:", caller_name)
    print("CUDA MEMORY")
    print("TOTAL MEMORY:", t)
    print("RESERVED:", r)
    print("FREE in RESERVER", f)
    print("------------------------")


# NOVELTY MEASURE (BC MEASURE)
# SNN simcos distance metric
# primary distance metric is L2-Norm
def simcos(A, k=50):
    num_sample, d = A.shape
    k = min(k, num_sample)
    dist_matrix = torch.cdist(A, A)
    nearest_dists, NN = torch.topk(dist_matrix, k=k, dim=1, largest=False)
    NN_one_hot = torch.nn.functional.one_hot(NN, num_classes=num_sample)
    NN_one_hot = torch.sum(NN_one_hot, dim=1).long()
    SNN_matrix = torch.logical_and(NN_one_hot.unsqueeze(1), NN_one_hot).long()
    SNN = torch.sum(SNN_matrix, dim=2)
    return SNN/k


def bc_item_selection(item_selection_list):
    return item_selection_list.float()


def bc_node_order(node_order_list):
    '''
    give max_score (which is num_nodes), to the first visited,
    then give num_nodes-1 score to second visited, etc...
    ofc first visited is always 0

    then  divide by num_nodes -> we get probability of visitation, which 
    is somewhat similar to what is used in rl algo for tsp-like problems
    '''
    num_sample, num_nodes = node_order_list.shape
    score_list = torch.arange(num_nodes, dtype=torch.float32) + 1
    score_list = score_list.flip(dims=(0,))

    total_score = torch.sum(score_list)
    bc = score_list[node_order_list]
    bc /= num_nodes
    return bc


def get_bc_var(node_order_list, item_selection_list):
    bc_node = bc_node_order(node_order_list)
    mean_bc_node = torch.mean(bc_node, dim=0, keepdim=True)
    var_bc_node = (bc_node-mean_bc_node)**2
    bc_node_final = torch.mean(var_bc_node, dim=1, keepdim=True)
    bc_item = bc_item_selection(item_selection_list)
    mean_bc_item = torch.mean(bc_item, dim=0, keepdim=True)
    var_bc_item = (bc_item-mean_bc_item)**2
    bc_item_final = torch.mean(var_bc_item, dim=1, keepdim=True)
    bc = 1-(bc_node_final+bc_item_final)/2
    return bc


def get_score_hv_contributions(f_list, negative_hv, nondom_archive=None, reference_point=None):
    real_num_sample, M = f_list.shape
    if nondom_archive is not None:
        f_list = combine_with_nondom(f_list, nondom_archive)
    num_sample, _ = f_list.shape
    f_list = f_list.numpy()
    # count hypervolume, first nondom sort then count, assign penalty hv too
    hv_contributions = np.full(shape=(num_sample,),fill_value=negative_hv, dtype=np.float32)
    nondom_idx = fast_non_dominated_sort(f_list)[0]
    norm_f_list = normalize(f_list)
    hv_contributions[nondom_idx] = get_hv_contributions(norm_f_list[nondom_idx], reference_point=None)
    hv_contributions = torch.from_numpy(hv_contributions).float()
    # hv_contributions = (1-novelty_w)+hv_contributions + novelty_w*novelty_score

    # prepare utility score
    score = hv_contributions.unsqueeze(1)
    score = score[:real_num_sample]
    return score


def cmp(a, b, crowding_distance_list):
    if crowding_distance_list[a] > crowding_distance_list[b]:
        return -1
    elif crowding_distance_list[a] < crowding_distance_list[b]:
        return 1
    return 0

def get_crowding_distance(score_list, fmax, fmin):
    num_sample, num_obj = score_list.shape
    if num_sample <= 2:
        return torch.zeros((num_sample,), dtype=torch.float32) + 999999
    arg_idx = torch.argsort(score_list, dim=0)
    obj_rank = torch.argsort(arg_idx, dim=0)  # scipy rankdata
    val_range = (fmax-fmin).view(1, num_obj)
    sorted_score_list, _ = torch.sort(score_list, dim=0)
    next_obj = sorted_score_list.gather(0, (obj_rank+1) % num_sample)
    prev_obj = sorted_score_list.gather(0, (obj_rank-1) % num_sample)
    dist_obj = next_obj-prev_obj
    is_extreme = torch.logical_or(obj_rank == 0, obj_rank == (num_sample-1))
    is_extreme = torch.sum(is_extreme, dim=1).bool()
    dist_obj /= val_range
    dist_obj = torch.sum(dist_obj, dim=1)
    dist_obj[is_extreme] = 999999
    return dist_obj

def get_score_nsga2(f_list, nondom_archive=None, reference_point=None):
    real_num_sample, M = f_list.shape
    if nondom_archive is not None:
        f_list = combine_with_nondom(f_list, nondom_archive)
    num_sample, _ = f_list.shape
    utility = get_utility(num_sample)
    rank = get_nondominated_rank(f_list)
    score = utility[rank][:real_num_sample].unsqueeze(1)
    return score