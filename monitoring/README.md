# PQC Security Monitoring Dashboard

## Overview
This monitoring setup uses Prometheus and Grafana to collect and visualize monitoring metrics for the Post-Quantum Zero-Trust Micro-Segmentation project.

## Tools Used
- Docker
- Docker Compose
- Prometheus
- Grafana

## Features
- Prometheus target availability monitoring
- Active time-series monitoring
- Prometheus memory usage monitoring
- Grafana dashboard visualization

## Setup
Run from the project root:

docker compose -f monitoring/docker-compose.yml up -d

## Access
- Prometheus: http://localhost:9090
- Prometheus Targets: http://localhost:9090/targets
- Grafana: http://localhost:3000

## Current Scope
Prometheus currently monitors its own metrics. Envoy and application-specific metrics have not yet been integrated.

## Dashboard Evidence
The Grafana dashboard screenshot is stored as `grafana-dashboard.png`.
