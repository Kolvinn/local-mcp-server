# Container & Volume Topology — Design Spec

**Date:** 2026-05-08
**Phase:** 2 — Container & Volume Topology Design
**Status:** Draft, awaiting user approval (Gate 1)

## 1. Overview

This spec defines the container, volume, and interaction topology for a multi-container agent system. The architecture uses a **symlink bridge** pattern: an orchestrator container mounts a shared `project-vol` plus per-agent `agent-{variation}-vol` volumes, and creates symlinks to dynamically grant agents file access without copying data or exposing the host filesystem. Each agent container runs headless (`sleep infinity`), uses **Flox** for system-level dependencies and **uv** for Python, and receives tasks via a JSON config file written to its volume. LangGraph provides orchestrator state management; the OpenCode agent framework runs headless on each agent container.

Nine agent variations run across a single Docker Compose network (`internal-net`), all backed by one shared Dockerfile template parameterized by variation. Zero host filesystem access, zero copies, zero container restarts for file grants.

