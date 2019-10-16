FROM python:3.5-slim
RUN apt-get update && apt-get install pandoc -y
COPY . /nsx2md
WORKDIR nsx2md
ENTRYPOINT [ "python", "./nsx2md.py" ]  
