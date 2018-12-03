import sys


for file_path in sys.argv[1:]:
    with open(file_path, 'r') as file:
        lines = []
        for line in file.readlines():
            if not line.startswith('Tags: '):
                lines.append(line)

    with open(file_path, 'w') as file:
        file.writelines(lines)
