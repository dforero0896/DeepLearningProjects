#!/usr/bin/env python
from torch import empty, set_grad_enabled, manual_seed
import math
set_grad_enabled(False)

def sigmoid(x):
    return 1. / (1 + (-x).exp())

class Module(object):
    def __init__(self):
        self.activation=None

    def forward(self, *args, **kwargs):
        raise NotImplementedError

    def backward(self, *args, **kwargs):
        raise NotImplementedError

    def param(self):
        return []

    def zero_grad(self):
        for param in self.param():
            if param.grad is None:
                param.grad = empty(param.shape).fill_(0)
            else:
                param.grad.fill_(0)


class LossMSE(Module):

    def __init__(self):
        super().__init__()

    def forward(self, prediction, target):
        error = (prediction - target)
        loss =  error.unsqueeze(1).matmul(error.unsqueeze(1).permute(0, 2, 1)).squeeze().sum()
        self.activation = error
        return loss
    
    def backward(self):
        return -2 * self.activation

    def __call__(self, prediction, target):
        return self.forward(prediction, target)

class ReLU(Module):

    def __init__(self, slope=1):

        super().__init__()
        self.slope = slope

    def forward(self, input):

        self.grad = empty(input.shape).fill_(0)
        self.grad[input > 0] = self.slope

        return self.slope * input.clamp(min=0)

    def backward(self, *gradwrtoutput):
        grad, = gradwrtoutput
        return grad * self.grad

    def __call__(self, input):
        return self.forward(input)
    
class Tanh(Module):

    def forward(self, input):
        self.grad = 1. / input.cosh().pow(2)
        return input.tanh()
    
    def backward(self, *gradwrtoutput):
        grad, = gradwrtoutput
        return grad * self.grad


    
    def __call__(self, input):
        return self.forward(input)
        

class Sigmoid(Module):

    def forward(self, input):
        s = sigmoid(input)
        self.grad = s * (1 - s)
        return s

    def backward(self, *gradwrtoutput):
        
        grad, = gradwrtoutput
        return  grad * self.grad

    def __call__(self, input):
        return self.forward(input)


class Linear(Module):

    def __init__(self, input_shape, output_units, batch_size):

        super().__init__()

        #Initialize weights

        self.weights = empty(size=(batch_size, output_units, input_shape)).normal_(mean=0, std=math.sqrt(2 / (input_shape + output_units) ))
        self.bias = empty(size=(batch_size, output_units)).normal_(mean=0, std=math.sqrt(2 / (input_shape + output_units) ))
        
        self.zero_grad()


    def forward(self, input):

        
        s = input.unsqueeze(1).matmul(self.weights.permute(0, 2, 1)).squeeze() + self.bias
        self.activation = (input, s)

        return s

    def backward(self, *gradwrtoutput):
        input, s = self.activation
        grad_s, = gradwrtoutput
        grad_x = grad_s.unsqueeze(1).matmul(self.weights).squeeze()

        self.weights.grad = self.weights.grad + grad_s[:, :, None] * input[:, None, :]
        self.bias.grad = self.bias.grad + grad_s

        return grad_x

    def param(self):
        return [self.weights, self.bias]

    def __call__(self, input):
        return self.forward(input)


class Sequential(Module):

    def __init__(self, *input):
        super().__init__()
        self.module_list=list(input)
        
        
    def forward(self, input):
        output = input
        for i, module in enumerate(self.module_list):
            output = module.forward(output)
        return output

    def backward(self, *gradwrtoutput):
        grad, = gradwrtoutput
        
        for i, module in enumerate(self.module_list[::-1]):
            
            grad = module.backward(grad)

    def param(self):
        params = []
        for module in self.module_list:
            params += module.param()
        return params

    def add(self, module):
        self.module_list.append(module)

    def __call__(self, input):
        return self.forward(input)

    def summary(self):
        print(f"Layer\tN. params")
        for module in self.module_list:
            print(f"{module.__class__.__name__}\t{sum([param.shape[-2] * param.shape[-1] for param in module.param()])}")


if __name__=='__main__':
    manual_seed(42)
    
    test = empty((10, 20)).fill_(1)
    target = empty((10, 40)).fill_(1)
    loss = LossMSE()
    linear = Linear(20, 40, 10)
    out = linear(test)
    out = loss(out, target)
    print(linear.backward(loss.backward())[:,0])
    
    

    
