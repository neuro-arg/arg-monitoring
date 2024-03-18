import numpy as np
import matplotlib.pyplot as plt

filename = input('Enter the filename: ')

data = np.load(filename)

for file in data.files:
    print(file)
    print(data[file])

# plot the raw results graph
plt.figure()
plt.plot(data['raw_results'])
plt.xlabel("Video number")
plt.ylabel("Max achieved SSIM")
plt.title("Threshold graph")
plt.show()
