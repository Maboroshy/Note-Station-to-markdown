FROM python:3.11-slim
RUN apt-get update && apt-get install pandoc -y && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY nsx2md.py /usr/local/bin/nsx2md.py
WORKDIR /data
ENTRYPOINT [ "python", "/usr/local/bin/nsx2md.py" ]
