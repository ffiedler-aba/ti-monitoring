#!/usr/bin/env bash
cd .. && docker compose -f docker-compose-dev.yml down && docker compose -f docker-compose-dev.yml builddocker compose -f docker-compose-dev.yml up -d