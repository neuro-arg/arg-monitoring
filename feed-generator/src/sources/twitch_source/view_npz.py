import numpy as np

filename = input('Enter the filename: ')

data = np.load(filename)

for file in data.files:
    print(file)
    print(data[file])
