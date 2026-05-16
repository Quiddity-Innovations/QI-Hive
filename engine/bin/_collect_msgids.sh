#!/usr/bin/env bash
# Collect all sent message_ids for both BP chats, both bots, all history.
set -e
echo "=== Tasuke (openclaw-gateway) -5161268852 ==="
journalctl --user -u openclaw-gateway --no-pager 2>/dev/null \
  | grep -oE 'sendMessage ok chat=-5161268852 message=[0-9]+' \
  | grep -oE 'message=[0-9]+' | cut -d= -f2 | sort -un | tr '\n' ' '
echo
echo "=== Tasuke (openclaw-gateway) -1003942950097 ==="
journalctl --user -u openclaw-gateway --no-pager 2>/dev/null \
  | grep -oE 'sendMessage ok chat=-1003942950097 message=[0-9]+' \
  | grep -oE 'message=[0-9]+' | cut -d= -f2 | sort -un | tr '\n' ' '
echo
echo "=== Kaze (openclaw-gateway-kaze) -5161268852 ==="
journalctl --user -u openclaw-gateway-kaze --no-pager 2>/dev/null \
  | grep -oE 'sendMessage ok chat=-5161268852 message=[0-9]+' \
  | grep -oE 'message=[0-9]+' | cut -d= -f2 | sort -un | tr '\n' ' '
echo
echo "=== Kaze (openclaw-gateway-kaze) -1003942950097 ==="
journalctl --user -u openclaw-gateway-kaze --no-pager 2>/dev/null \
  | grep -oE 'sendMessage ok chat=-1003942950097 message=[0-9]+' \
  | grep -oE 'message=[0-9]+' | cut -d= -f2 | sort -un | tr '\n' ' '
echo
