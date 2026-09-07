import os

for root, dirs, files in os.walk('.'):
    for name in files:
        print(os.path.join(root, name))