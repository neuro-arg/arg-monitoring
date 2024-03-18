"""
Arbitrary correction script. Adjust values until you get a graph that
"makes sense"
"""

import numpy as np
import matplotlib.pyplot as plt

filename = input('Enter the filename: ')

data = np.load(filename)

for file in data.files:
    print(file)
    print(data[file])

better_results = data['raw_results'][np.all(data['raw_results'] >= 0.7, axis=1)]

# get means / mins of better results
better_means = better_results.mean(axis=0)
better_mins = better_results.min(axis=0)

print('Better means:')
print(better_means)
print('Better mins:')
print(better_mins)
print('Saving as better_results.npz')
np.savez('better_results.npz',
         thresholds=np.array(list(zip(better_means, better_mins))),
         mins=better_mins,
         raw_results=better_results)

# plot the raw results graph
plt.figure()
plt.plot(better_results)
plt.xlabel("Video number")
plt.ylabel("Max achieved SSIM")
plt.title("Threshold graph")
plt.show()
