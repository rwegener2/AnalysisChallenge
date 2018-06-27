# our base image
FROM python:3

# copy in scripts and data
RUN mkdir /home/output/
COPY Docker_code/ /home/
RUN pip install -r /home/requirements.txt

# run the application
CMD ["python", "/home/boundary_script_docker.py"]
