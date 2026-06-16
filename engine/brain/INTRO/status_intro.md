# QI Brain — Ecosystem intelligence API

## What is QI Brain?

QI Brain is the intelligence layer of the QI ecosystem. It exposes a FastAPI service on port 9010 and a SQLite-backed memory store of decisions, features, sessions, and project state. The QI Hive Dashboard, Claude Code sessions, and the agentic sub-agents all read from and write to Brain via the qi.* MCP tools.

## Status

Live — FastAPI service on port 9010 backing QI Hive Dashboard.

## Where it lives

- **Path:** `C:\QIH\engine\brain`
- **Port:** 9010
- **Allocated block:** 9010-9019

## Role in the QI Ecosystem

QI Brain is one of the projects orchestrated by QI Hive. See the QI Ecosystem Map
(`C:\QIH\ecosystem\QI_Ecosystem_Map.md`) for the full port table, ownership matrix,
and integration contracts. This page will be expanded with the project's full feature
matrix, blueprint diagrams, and tech-stack deep-dive as the work progresses.
