"""Generic networks that approximate a function, used for supervised learning"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/30_agents/60_approximators/11_approximators.ipynb.

# %% auto 0
__all__ = ['BaseModule', 'LinearModel', 'MLP', 'Transformer', 'LlamaRotaryEmbedding', 'rotate_half', 'apply_rotary_pos_emb',
           'CausalSelfAttention', 'find_multiple', 'MLP_block', 'RMSNorm', 'Block']

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 3
# import logging
# logging_level = logging.DEBUG

from abc import ABC, abstractmethod
from typing import Union, Dict, Literal
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

import time

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 4
# TODO: Merge with base from RL networks to avoid duplicaiotn of code

class BaseModule(nn.Module):
    def __init__(self):
        super().__init__()

    @staticmethod
    def select_activation(activation):
        """ Select the activation function based on input string """
        activation = activation.lower()  # Convert input to lowercase for consistency
        if activation == "relu":
            return nn.ReLU
        elif activation == "sigmoid":
            return nn.Sigmoid
        elif activation == "tanh":
            return nn.Tanh
        elif activation == "elu":
            return nn.ELU
        elif activation == "leakyrelu":
            return nn.LeakyReLU
        elif activation == "identity":
            return nn.Identity
        else:
            raise ValueError(f"Activation function {activation} not recognized")

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 5
class LinearModel(BaseModule):
    """Linear regression model"""

    def __init__(self, 
            input_size: int, # number of features
            output_size: int, # number of outputs/actions
            relu_output: bool = False): # whether to apply ReLU activation to the output
        super().__init__()
        self.l1=nn.Linear(input_size, output_size)
        if relu_output:
            self.final_activation = nn.ReLU()
        else:
            self.final_activation = nn.Identity()
            
    def forward(self,x):
        out=self.l1(x)
        out=self.final_activation(out)
        return out

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 6
class MLP(BaseModule):

    """ Multilayer perceptron model """

    def __init__(self,
                    input_size: int, # number of features
                    output_size: int, # number of outputs/actions
                    hidden_layers: list, # list of number of neurons in each hidden layer
                    drop_prob: float = 0.0, # dropout probability
                    batch_norm: bool = False, # whether to apply batch normalization
                    relu_output: bool = False): # whether to apply ReLU activation to the output
        super().__init__()

        # List of layers
        layers = []

        last_size = input_size
        for num_neurons in hidden_layers:
            layers.append(nn.Linear(last_size, num_neurons))
            layers.append(nn.ReLU())
            if batch_norm:
                layers.append(nn.BatchNorm1d(num_neurons))
            layers.append(nn.Dropout(p=drop_prob))
            last_size = num_neurons

        # Output layer
        layers.append(nn.Linear(last_size, output_size))
        if relu_output:
            layers.append(nn.ReLU()) # output is non-negative
        else:
            layers.append(nn.Identity())

        # Combine layers
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 7
class Transformer(BaseModule):

    """ Multilayer perceptron model """

    def __init__(self,
                    input_size: int, # number of (time steps, features)
                    output_size: int, # number of outputs/actions

                    max_context_length: int = 128, #  maximum context lenght during inference
                    n_layer: int = 3, # number of layers in the transformer
                    n_head: int = 8, # number of heads per layer
                    n_embd_per_head: int = 32, # number of embedding per head
                    rope_scaling: Dict | None = None, # whether to use rope scaling, not implemented yet

                    min_multiple = 256, # minimum multiple for neurons in the MLP block of the transformer
                    gating = True, # Whether to apply the gating mechanism from the original Llama model (used in LagLlama)

                    drop_prob: float = 0.0, # dropout probability
                    final_activation: Literal["relu", "sigmoid", "tanh", "elu", "leakyrelu", "identity"] = "identity" # final activation function
                    ): # whether to apply ReLU activation to the output

        super().__init__()

        block_size = max_context_length
        input_size = input_size[1] # we only consider the number of features

        self.param_proj = nn.Linear(n_embd_per_head * n_head, output_size) # final projection layer for output

        self.transformer = nn.ModuleDict(
            dict(
                wte=nn.Linear(
                    input_size, n_embd_per_head * n_head # Initial projection from input to embedding space
                ),
                h=nn.ModuleList([Block(n_embd_per_head, n_head, block_size, drop_prob, min_multiple = min_multiple, gating=gating) for _ in range(n_layer)]),
                ln_f=RMSNorm(n_embd_per_head * n_head),
            )
        )

        self.final_activation = self.select_activation(final_activation)()

        # not _init_weights used since we are using the default initialization.

    def forward(    self,
                    x: torch.Tensor,) -> torch.Tensor:

        (B, T, C) = x.size()

        x = self.transformer.wte(
            x
        )

        for block in self.transformer.h:
            x = block(x)

        output = self.param_proj(
            x
        ) 

        output = self.final_activation(output)

        output = output[:, -1, :] # we use the last time dimension as the output
             
        return output

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 8
class LlamaRotaryEmbedding(torch.nn.Module):

    """
    Rotary positional embeddings (RoPE) based on https://arxiv.org/abs/2104.09864
    Code following the implementation in https://github.com/time-series-foundation-models/lag-llama

    """

    def __init__(self, dim, max_position_embeddings=2048, base=10000, device=None):
        super().__init__()

        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base
        inv_freq = 1.0 / (
            self.base ** (torch.arange(0, self.dim, 2).float().to(device) / self.dim)
        )
        self.register_buffer("inv_freq", inv_freq, persistent=False)

        self._set_cos_sin_cache(
            seq_len=max_position_embeddings,
            device=self.inv_freq.device,
            dtype=torch.get_default_dtype(),
        )

    def _set_cos_sin_cache(self, seq_len, device, dtype):
        self.max_seq_len_cached = seq_len
        t = torch.arange(
            self.max_seq_len_cached, device=device, dtype=self.inv_freq.dtype
        )

        freqs = torch.einsum("i,j->ij", t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        self.register_buffer(
            "cos_cached", emb.cos()[None, None, :, :].to(dtype), persistent=False
        )
        self.register_buffer(
            "sin_cached", emb.sin()[None, None, :, :].to(dtype), persistent=False
        )

    def forward(self, device, dtype, seq_len=None):
        if seq_len > self.max_seq_len_cached:
            self._set_cos_sin_cache(seq_len=seq_len, device=device, dtype=dtype)

        return (
            self.cos_cached[:, :, :seq_len, ...].to(dtype=dtype),
            self.sin_cached[:, :, :seq_len, ...].to(dtype=dtype),
        )

def rotate_half(x):
    """Rotates half the hidden dims of the input."""
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb(q, k, cos, sin, position_ids):
    # The first two dimensions of cos and sin are always 1, so we can `squeeze` them.
    cos = cos.squeeze(1).squeeze(0)  # [seq_len, dim]
    sin = sin.squeeze(1).squeeze(0)  # [seq_len, dim]
    cos = cos[position_ids].unsqueeze(1)  # [bs, 1, seq_len, dim]
    sin = sin[position_ids].unsqueeze(1)  # [bs, 1, seq_len, dim]
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 9
class CausalSelfAttention(nn.Module):

    """ Causeal self-attention module
    Based on the implementation in https://github.com/time-series-foundation-models/lag-llama,
    without usage of kv_cache since we always make a prediction for only the next step
    """

    def __init__(self, n_embd_per_head, n_head, block_size, dropout) -> None:
        super().__init__()
        # query projections for all heads, but in a batch
        self.q_proj = nn.Linear(
            n_embd_per_head * n_head,
            n_embd_per_head * n_head,
            bias=False,
        )
        # key, value projections
        self.kv_proj = nn.Linear(
            n_embd_per_head * n_head,
            2 * n_embd_per_head * n_head,
            bias=False,
        )
        # output projection
        self.c_proj = nn.Linear(
            n_embd_per_head * n_head,
            n_embd_per_head * n_head,
            bias=False,
        )

        self.n_head = n_head
        self.n_embd_per_head = n_embd_per_head
        self.block_size = block_size
        self.dropout = dropout

        self.rope_scaling=None

        self._init_rope()

    def _init_rope(self):
        if self.rope_scaling is None:
            self.rotary_emb = LlamaRotaryEmbedding(
                self.n_embd_per_head, max_position_embeddings=self.block_size
            )

        else:
            raise NotImplementedError("RoPE scaling is not yet implemented")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # batch size, sequence length, embedding dimensionality (n_embd)

        B, T, C = x.size()

        # calculate query, key, values for all heads in batch and move head forward to be the batch dim
        q = self.q_proj(x)
        k, v = self.kv_proj(x).split(self.n_embd_per_head * self.n_head, dim=2)

        
        k = k.view(B, -1, self.n_head, self.n_embd_per_head).transpose(
            1, 2
        )  # (B, nh, T, hs)
        q = q.view(B, -1, self.n_head, self.n_embd_per_head).transpose(
            1, 2
        )  # (B, nh, T, hs)
        v = v.view(B, -1, self.n_head, self.n_embd_per_head).transpose(
            1, 2
        )  # (B, nh, T, hs)

        if self.rotary_emb is not None:
            cos, sin = self.rotary_emb(device=v.device, dtype=v.dtype, seq_len=T)
            q, k = apply_rotary_pos_emb(q, k, cos, sin, position_ids=None)


        y = F.scaled_dot_product_attention(
            q, k, v, attn_mask=None, dropout_p=self.dropout, is_causal=True
        )
        
        # # debug
        # if not torch.isfinite(y).all():
        #     print("y is not finite")
        #     print(y)
        #     print(q)
        #     print(k)
        #     print(v)

        # re-assemble all head outputs side by side
        y = y.transpose(1, 2).contiguous().view(B, T, C)

        # output projection
        y = self.c_proj(y)

        return y

def find_multiple(n: int, k: int) -> int:
    if n % k == 0:
        return n
    return n + k - (n % k)

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 10
class MLP_block(nn.Module):
    def __init__(self, n_embd_per_head, n_head, min_multiple = 256, gating = True) -> None:
        super().__init__()
        hidden_dim = 4 * n_embd_per_head * n_head
        n_hidden = int(2 * hidden_dim / 3)
        self.gating = gating
        
        n_hidden = find_multiple(n_hidden, min_multiple)

        self.c_fc1 = nn.Linear(
            n_embd_per_head * n_head, n_hidden, bias=False
        )
        if gating:
            self.c_fc2 = nn.Linear(
                n_embd_per_head * n_head, n_hidden, bias=False
            )
        
        self.c_proj = nn.Linear(
            n_hidden, n_embd_per_head * n_head, bias=False
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.gating:
            x = F.silu(self.c_fc1(x)) * self.c_fc2(x)
        else:
            x = F.silu(self.c_fc1(x))
        x = self.c_proj(x)
        return x

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 11
class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization as implemented in https://github.com/time-series-foundation-models/lag-llama.

    Derived from https://github.com/bzhangGo/rmsnorm/blob/master/rmsnorm_torch.py. BSD 3-Clause License:
    https://github.com/bzhangGo/rmsnorm/blob/master/LICENSE.
    """

    def __init__(self, size: int, dim: int = -1, eps: float = 1e-5) -> None:
        super().__init__()
        self.scale = nn.Parameter(torch.ones(size))
        self.eps = eps
        self.dim = dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm_x = x.to(torch.float32).pow(2).mean(dim=self.dim, keepdim=True)
        x_normed = x * torch.rsqrt(norm_x + self.eps)
        output = (self.scale * x_normed).type_as(x)
        return output

# %% ../nbs/30_agents/60_approximators/11_approximators.ipynb 12
class Block(nn.Module):
    def __init__(self, n_embd_per_head, n_head, block_size, dropout, min_multiple = 256, gating=True) -> None:
        super().__init__()
        self.rms_1 = RMSNorm(n_embd_per_head * n_head)
        self.attn = CausalSelfAttention(n_embd_per_head, n_head, block_size, dropout)
        self.rms_2 = RMSNorm(n_embd_per_head * n_head)
        self.mlp = MLP_block(n_embd_per_head, n_head, min_multiple = min_multiple, gating=gating)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.rms_1(x))
        y = x + self.mlp(self.rms_2(x))
        return y
