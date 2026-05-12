services:
  orchestrator:
    image: ?????
    container_name: orchestrator
    volumes:
      - project-vol:/home/dev/app:rw
      - type: volume
        source: agent-vol
        target: workspace
        volume:
          subpath: orchestrator

  agent1:
    image: ?????
    container_name: agent1
    volumes:
      - project-vol:/home/dev/app:ro
      - type: volume
        source: agent-vol
        target: workspace
        volume:
          subpath: agent1

volumes:
  agent-vol:
    - external: true
volumes:
  project-vol:
    - external: true
