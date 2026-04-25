FROM framework-opencode:latest


COPY --chown=dev:dev ./dev/mcp-server/ /home/dev/app/
USER dev

#SHELL ["/bin/bash" , "-c"]
RUN conda create -n dev1

#RUN conda activate dev1
ENV VIRTUAL_ENV=/home/dev/conda/envs/dev1/bin
RUN conda install --name dev1 -c conda-forge python uv

#install -c conda-forge bun && 


# Now you can use them immediately
WORKDIR /home/dev/app/

RUN uv --version
RUN cd src && uv sync --system
#THIS ASSUMES REQUIREMENTS.TXT HAS ALREADY BEEN GENERATED
#RUN conda run -n dev1 uv pip install -r requirements.txt




CMD ["sleep", "infinity"]
