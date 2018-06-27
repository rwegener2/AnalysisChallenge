# AnalysisChallenge

This repository contains the folder Docker\_code which contains the files that get copied to the docker container upon build.  The folder Manual\_code folder contains the same files that can be run outside of a container if that is preferable.

### boundary_select.py

The script inside both folders is can be run with the command:

	python boundary_select.py

This will run the default arguments.  The -db and -sb flags can be used to set the day\_buffer and spatial\_buffer variables if desired.  (See script or python boundary_script.py -h for details)

### Docker container

To build the container enter the folder where the Dockerfile is located and run:

	docker build -t boundary .

(The tag is optional but will be used in this readme for clarity.)

Once the container is built the script can be run using the default settings for day\_buffer and spatial\_buffer using:

	docker run -v "/where/output/is/saved/":/home/output boundary

If you would like those variables to be set manually by overriding the default CMD of the Dockerfile and running the script with variable flags.  For example:

	docker run -v "/where/output/is/saved/":/home/output boundary python /home/boundary_select.py -db 5 -sb 0.0002

The output of the code will be saved in the user's directory /where/output/is/saved/.  This folder should hold the output jsons only.
