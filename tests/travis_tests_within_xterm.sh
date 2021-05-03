#!/bin/bash

rm -f success
d="$(pwd)"

pytest -xs . && touch "$d/success"

