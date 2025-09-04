#!/usr/bin/env bash
cd .. &&docker compose -f docker-compose.yml down && docker compose -f docker-compose.yml builddocker compose -f docker-compose.yml up -d