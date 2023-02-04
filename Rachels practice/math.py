import numpy as np
import matplotlib
# single line comment typically in between things
'''
multi line comments
typically at the top, explaining what code does
This code tests the assigning of your variables and casting them to other variable.
Author: Rachel S.
'''
var = 1
var2 = 1.0
var3 = '1'
print(var)
print(var2)
print(var3)
print(str(var) + ' ' + str(var2) + ' ' + var3)
var4 = var + var2 + int(var3)
print(var4)
print(np.round(np.cos(np.pi/2)))
print(7%3)
x = np.linspace(-100,100,1)
y = x**2
print(y)
# matplotlib.pyplot.plot(x,y,'r', linewidth=1, marker = 'i')
