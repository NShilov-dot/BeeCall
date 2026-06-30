#!/usr/bin/env bash
#
# SIP / Asterisk trunk diagnostics for the dograh-asterisk container.
#
# Answers the two questions that come up whenever a SIP trunk "won't connect":
#   1. Can this network even reach a SIP provider, or is it firewalled?
#   2. Is the PJSIP trunk actually registered?
#
# Background: the corporate Beeline UZ network silently drops outbound traffic
# to SIP ports 5060/5061 while leaving 443 open, so any trunk on standard ports
# fails identically here. The fastest confirmation is to re-run this from a phone
# hotspot — see `scripts/sip-diag.sh --register`.
#
# Usage:
#   scripts/sip-diag.sh              # full read-only sweep
#   scripts/sip-diag.sh --register   # force a re-registration, then poll status
#                                    # (run this after switching to the hotspot)
#
# Env overrides:
#   ASTERISK_CONTAINER  (default: dograh-asterisk)
#   REG_NAME            (default: zadarma-reg)     PJSIP registration object
#   SIP_HOST            (default: sip.zadarma.com) provider host to probe

set -euo pipefail

CONTAINER="${ASTERISK_CONTAINER:-dograh-asterisk}"
REG_NAME="${REG_NAME:-zadarma-reg}"
SIP_HOST="${SIP_HOST:-sip.zadarma.com}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
bad()  { echo -e "  ${RED}✗${NC} $*"; }
warn() { echo -e "  ${YELLOW}!${NC} $*"; }
hdr()  { echo -e "\n${BOLD}== $* ==${NC}"; }

ast() { docker exec "$CONTAINER" asterisk -rx "$1" 2>&1; }

# TCP reachability from inside the container via bash /dev/tcp (5s timeout).
# Prints OPEN / REFUSED / BLOCKED so we can tell "filtered" from "port closed".
probe_tcp() {
  local host="$1" port="$2"
  docker exec "$CONTAINER" bash -c \
    "timeout 5 bash -c 'exec 3<>/dev/tcp/$host/$port && echo OPEN' 2>&1 || true"
}
classify() {
  case "$1" in
    *OPEN*)    echo "OPEN" ;;
    *refused*) echo "REFUSED" ;;
    *)         echo "BLOCKED" ;;
  esac
}

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" >/dev/null 2>&1; then
  bad "Container '$CONTAINER' not found. Start it: docker compose -f docker-compose-asterisk.yaml up -d"
  exit 1
fi
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" != "true" ]; then
  bad "Container '$CONTAINER' is not running. Start it: docker compose -f docker-compose-asterisk.yaml up -d"
  exit 1
fi
ok "Container '$CONTAINER' is running"

hdr "DNS"
dns="$(docker exec "$CONTAINER" getent hosts "$SIP_HOST" 2>&1 | head -1 || true)"
if [ -n "$dns" ]; then ok "$SIP_HOST -> ${dns%% *} ($dns)"; else bad "cannot resolve $SIP_HOST"; fi
ip="$(echo "$dns" | awk '{print $1}')"

hdr "SIP-port reachability (the firewall test)"
for port in 5060 5061; do
  res="$(classify "$(probe_tcp "${ip:-$SIP_HOST}" "$port")")"
  case "$res" in
    OPEN)    ok    "tcp/$port -> OPEN (SIP reachable)";;
    REFUSED) warn  "tcp/$port -> REFUSED (reachable, no TCP listener — try UDP/registration)";;
    BLOCKED) bad   "tcp/$port -> BLOCKED/timeout (silently dropped — classic SIP-port firewall)";;
  esac
done
res443="$(classify "$(probe_tcp "${ip:-$SIP_HOST}" 443)")"
if [ "$res443" != "BLOCKED" ]; then
  ok "tcp/443 -> $res443 (general egress works → only SIP ports are filtered)"
else
  warn "tcp/443 -> BLOCKED too (broader egress problem, not just SIP)"
fi

hdr "Trunk registration"
ast 'pjsip show registrations'

if [ "${1:-}" = "--register" ]; then
  hdr "Forcing re-registration of '$REG_NAME'"
  ast "pjsip send unregister $REG_NAME" >/dev/null || true
  ast "pjsip send register $REG_NAME"
  for i in 1 2 3 4 5 6; do
    sleep 2
    line="$(ast 'pjsip show registrations' | grep -i "$REG_NAME" || true)"
    echo "  [$((i*2))s] $line"
    if echo "$line" | grep -qi 'Registered'; then
      ok "Registered! SIP works on this network (so the dev failure was the firewall)."
      exit 0
    fi
  done
  bad "Still not registered after 12s. If you're on the hotspot, the issue isn't only the firewall — check Zadarma creds / that SIP is enabled in their panel."
fi
