FROM framework-opencode:latest


#COPY --chown=dev:dev ./dev/mcp-server/ /home/dev/app/
USER dev
RUN mkdir -p /home/dev/app
#SHELL ["/bin/bash" , "-c"]
RUN conda create -n dev1

#RUN conda activate dev1
ENV VIRTUAL_ENV=/home/dev/conda/envs/dev1
RUN conda install --name dev1 -c conda-forge uv

#install -c conda-forge bun && 


# Now you can use them immediately
WORKDIR /home/dev/app/

#RUN uv --version
#RUN cd src && uv sync --system
#THIS ASSUMES REQUIREMENTS.TXT HAS ALREADY BEEN GENERATED
#RUN cd src && conda run uv pip install pyproject.toml  --system


CMD ["sleep", "infinity"]

