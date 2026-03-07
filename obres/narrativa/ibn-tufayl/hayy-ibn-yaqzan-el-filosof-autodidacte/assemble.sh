#!/bin/bash
DIR="$(dirname "$0")"
{
  printf '# Hayy ibn Yaqzan — El filòsof autodidacte\n'
  printf '*Ibn Tufayl (Abu Bakr Muhammad ibn Tufail al-Qasi)*\n\n'
  printf 'Traduït al català per Biblioteca Arion, a partir de la versió anglesa de Simon Ockley (1708)\n\n'
  printf '---\n\n'
  cat "$DIR/_part1_intro.md"
  printf '\n---\n\n'
  cat "$DIR/_part2_historia1.md"
  printf '\n'
  cat "$DIR/_part3_historia2.md"
  printf '\n'
  cat "$DIR/_part4_historia3.md"
  printf '\n---\n\n'
  printf '*Traducció al català de domini públic — Biblioteca Universal Arion, 2026.*\n'
} > "$DIR/traduccio.md"
