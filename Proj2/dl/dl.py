#!/usr/bin/env python
from torch import empty, set_grad_enabled, manual_seed
import math
set_grad_enabled(False)

def sigmoid(x):
    return 1. / (1 + (-x).exp())

class nTensor(empty(0).__class__):
    def __init__(self, *args, **kwargs):
        super(nTensor, self).__init__(*args)
        self.createdby = None

    def set_createdby(self, instance):
        self.createdby = instance
        
class Module(object):
    def __init__(self):
        self.input = None
        self.output = None

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def forward(self, *args, **kwargs):
        raise NotImplementedError

    def backward_(self, *args, **kwargs):
        raise NotImplementedError

    def backward(self):
        grad = self.backward_()
        module = self.input.createdby
        while module:
            grad = module.backward_(grad)
            module = module.input.createdby

    def param(self):
        return []

    def zero_grad(self):
        for param in self.param():
            if param.grad is None:
                param.grad = nTensor(size=param.shape).fill_(0)
            else:
                param.grad.fill_(0)


class LossMSE(Module):

    def __init__(self):
        super(Module, self).__init__()
        self.error = None

    def forward(self, prediction, target):
        self.input = prediction
        self.error = (prediction - target)
        self.output =  self.error.pow(2).mean()
        self.output.set_createdby(self)
        return self.output
    
    def backward_(self):
        #return -2 * self.error # this gives - twice the gradient as pytorch, weird
        return self.error
    
class ReLU(Module):

    def __init__(self, slope=1):

        super(Module, self).__init__()
        self.slope = slope

    def forward(self, input):
        self.input = input
        self.grad = nTensor(size=input.shape).fill_(0)
        self.grad[input > 0] = self.slope
        self.output = self.slope * input.clamp(min=0)
        self.output.set_createdby(self)
        return self.output

    def backward_(self, *gradwrtoutput):
        grad, = gradwrtoutput
        return grad * self.grad
    
class Tanh(Module):

    def forward(self, input):
        self.input = input
        self.grad = 1. / input.cosh().pow(2)
        self.output = input.tanh()
        self.output.set_createdby(self)
        return self.output
    
    def backward_(self, *gradwrtoutput):
        grad, = gradwrtoutput
        return grad * self.grad     

class Sigmoid(Module):

    def forward(self, input):
        self.input = input
        s = sigmoid(input)
        self.grad = s * (1 - s)
        self.output = s
        self.output.set_createdby(self)
        return self.output

    def backward_(self, *gradwrtoutput):
        
        grad, = gradwrtoutput
        return  grad * self.grad

class Linear(Module):

    def __init__(self, input_features, output_features):

        super(Module, self).__init__()

        #Initialize weights
        self.sqrtk = math.sqrt(1 / input_features)
        self.weights = nTensor(size=(output_features, input_features)).uniform_(-self.sqrtk, self.sqrtk)
        self.bias = nTensor(size=(output_features,)).uniform_(-self.sqrtk, self.sqrtk)
        
        self.zero_grad()


    def forward(self, input):
        self.input = input
        s = input.matmul(self.weights.t()).squeeze() + self.bias
        self.output = s
        self.output.set_createdby(self)
        return self.output

    def backward_(self, *gradwrtoutput):
        grad_s, = gradwrtoutput
        grad_x = grad_s.matmul(self.weights)

        self.weights.grad = self.weights.grad + (grad_s[:, :, None] * self.input[:, None, :]).mean(axis=0)
        self.bias.grad = self.bias.grad + grad_s.mean(axis=0)

        return grad_x

    def param(self):
        return [self.weights, self.bias]

class Sequential(Module):

    def __init__(self, *input):
        super(Module, self).__init__()
        self.module_list=list(input)
        
        
    def forward(self, input):
        self.input = input
        self.input.set_createdby(None)
        output = input
        for i, module in enumerate(self.module_list):
            output = module(output)
        self.output = output
        return self.output

    def backward(self, *gradwrtoutput):
        grad, = gradwrtoutput
        for i, module in enumerate(self.module_list[::-1]):
            grad = module.backward_(grad)

    def param(self):
        params = []
        for module in self.module_list:
            params += module.param()
        return params

    def add(self, module):
        self.module_list.append(module)

    def __getitem__(self, i):
        return self.module_list[i]

    def summary(self):
        print(f"Layer\tN. params")
        for module in self.module_list:
            print(f"{module.__class__.__name__}\t{sum([param.shape[-2] * param.shape[-1] for param in module.param()])}")    
